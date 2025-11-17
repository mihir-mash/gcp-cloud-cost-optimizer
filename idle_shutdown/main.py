import os
import json
import time
import logging
import google.auth
from googleapiclient import discovery
from google.cloud import monitoring_v3

def get_cpu_usage(project, zone, instance_id, minutes=60):
    client = monitoring_v3.MetricServiceClient()
    now = int(time.time())
    start_seconds = now - minutes * 60
    end_seconds = now

    interval = {
        "start_time": {"seconds": int(start_seconds)},
        "end_time": {"seconds": int(end_seconds)}
    }

    name = f"projects/{project}"
    # filter on instance id (resource label)
    filter_str = f'metric.type="compute.googleapis.com/instance/cpu/utilization" AND resource.labels.instance_id="{instance_id}"'

    try:
        series_iter = client.list_time_series(
            request={
                "name": name,
                "filter": filter_str,
                "interval": interval,
                "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL
            }
        )
        vals = []
        for s in series_iter:
            for p in s.points:
                v = getattr(p.value, "double_value", None)
                if v is not None:
                    vals.append(v)
        if not vals:
            return 0.0
        return sum(vals) / len(vals)
    except Exception:
        logging.exception("monitoring query failed")
        return 0.0

def main(request):
    # detect project robustly
    try:
        credentials, default_project = google.auth.default()
    except Exception:
        credentials, default_project = (None, None)
    project = os.environ.get("GCP_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT") or default_project or os.environ.get("PROJECT")

    # config
    cpu_threshold = float(os.environ.get("CPU_THRESHOLD", "5"))
    dry_run = os.environ.get("DRY_RUN", "true").lower() == "true"

    compute = discovery.build("compute", "v1")
    actions = []

    # get zones; if fails, fall back to common zone
    try:
        zones_resp = compute.zones().list(project=project).execute()
        zones = [z["name"] for z in zones_resp.get("items", [])] if "items" in zones_resp else ["us-central1-a"]
    except Exception:
        zones = ["us-central1-a"]

    for zone in zones:
        try:
            resp = compute.instances().list(project=project, zone=zone).execute()
        except Exception:
            logging.exception(f"could not list instances in zone {zone}")
            continue

        if "items" not in resp:
            continue

        for vm in resp["items"]:
            name = vm.get("name")
            instance_id = vm.get("id")
            labels = vm.get("labels", {})
            status = vm.get("status", "UNKNOWN")

            # only act on VMs labelled auto-shutdown=true
            if labels.get("auto-shutdown") != "true":
                actions.append(f"Skipping {name} (no label)")
                continue

            cpu_avg_12h = get_cpu_usage(project, zone, instance_id, minutes=60*12)
            cpu_pct = cpu_avg_12h * 100.0

            if cpu_pct < cpu_threshold:
                if dry_run:
                    actions.append(f"[DRY RUN] Would stop {name} (CPU {cpu_pct:.2f}%)")
                else:
                    try:
                        compute.instances().stop(project=project, zone=zone, instance=name).execute()
                        actions.append(f"Stopped {name} (CPU {cpu_pct:.2f}%)")
                    except Exception:
                        logging.exception(f"failed to stop {name}")
                        actions.append(f"Error stopping {name}")
            else:
                actions.append(f"{name} active (CPU {cpu_pct:.2f}%)")

    return (json.dumps({"result": actions}), 200, {"Content-Type": "application/json"})
