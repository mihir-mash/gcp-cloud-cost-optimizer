import os
import json
import time
import logging
import google.auth
from google.cloud import bigquery, monitoring_v3
from googleapiclient import discovery

def query_billing(project, dataset):
    client = bigquery.Client(project=project)
    table_pattern = f"`{project}.{dataset}.gcp_billing_export_v1_*`"
    sql = f"""
    WITH raw AS (
      SELECT
        TIMESTAMP(usage_start_time) AS usage_start,
        resource.name AS resource_name,
        cost
      FROM {table_pattern}
      WHERE TIMESTAMP(usage_start_time) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)
    )
    SELECT
      REGEXP_EXTRACT(resource_name, r'instances/([^/]+)$') AS instance_name,
      SUM(cost) AS cost_24h
    FROM raw
    WHERE resource_name LIKE '%compute.googleapis.com/projects/%/zones/%/instances/%'
    GROUP BY instance_name
    ORDER BY cost_24h DESC
    """
    try:
        query_job = client.query(sql)
        rows = list(query_job.result())
        return {row.instance_name: float(row.cost_24h) for row in rows if row.instance_name}
    except Exception:
        return {}

def get_cpu_avg(project, instance_id, minutes=60):
    client = monitoring_v3.MetricServiceClient()
    now = int(time.time())
    start_seconds = now - minutes * 60
    end_seconds = now
    interval = {
        "start_time": {"seconds": int(start_seconds)},
        "end_time": {"seconds": int(end_seconds)}
    }
    name = f"projects/{project}"
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
        return 0.0

def estimate_cost_by_machine(machine_type):
    mapping = {
        "e2-micro": 0.0076, "e2-small": 0.0166, "e2-medium": 0.0332,
        "n1-standard-1": 0.0475, "n1-standard-2": 0.0950, "e2-standard-4": 0.05,
        "e2-standard-2": 0.03
    }
    return mapping.get(machine_type, 0.05)

def send_report_via_sendgrid(sendgrid_key, admin_email, from_email, report):
    if not sendgrid_key or not admin_email or not from_email:
        logging.info("SendGrid or emails not configured; skipping send.")
        return {"sent": False, "reason": "missing_config"}
    url = "https://api.sendgrid.com/v3/mail/send"
    body = {
        "personalizations": [{"to": [{"email": admin_email}], "subject": f"Daily Cost Report for {report.get('project','project')}"}],
        "from": {"email": from_email},
        "content": [{"type": "text/plain", "value": json.dumps(report, indent=2)}]
    }
    headers = {"Authorization": f"Bearer {sendgrid_key}", "Content-Type": "application/json"}
    try:
        import requests
        resp = requests.post(url, json=body, headers=headers, timeout=15)
        logging.info(f"SendGrid status: {resp.status_code}, body: {resp.text}")
        if resp.status_code in (200, 202):
            return {"sent": True, "status": resp.status_code}
        else:
            return {"sent": False, "status": resp.status_code, "body": resp.text}
    except Exception as e:
        logging.exception("SendGrid request failed")
        return {"sent": False, "exception": str(e)}

def main(request):
    credentials, default_project = google.auth.default()
    project = os.environ.get("GCP_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT") or default_project
    dataset = os.environ.get("BQ_DATASET", "billing_export")
    cpu_threshold = float(os.environ.get("CPU_THRESHOLD", 5))
    dry_run = os.environ.get("DRY_RUN", "true").lower() == "true"
    admin_email = os.environ.get("ADMIN_EMAIL", "")
    sendgrid_key = os.environ.get("SENDGRID_API_KEY", "")
    from_email = os.environ.get("FROM_EMAIL", "")

    compute = discovery.build("compute", "v1")
    try:
        zones_resp = compute.zones().list(project=project).execute()
        zones = [z["name"] for z in zones_resp.get("items", [])] if "items" in zones_resp else ["us-central1-a"]
    except Exception:
        zones = ["us-central1-a"]

    billing_map = query_billing(project, dataset)

    instances_report = []
    total_cost = 0.0

    for zone in zones:
        try:
            resp = compute.instances().list(project=project, zone=zone).execute()
        except Exception:
            continue
        if "items" not in resp:
            continue
        for vm in resp["items"]:
            name = vm["name"]
            labels = vm.get("labels", {})
            instance_id = vm.get("id")
            machine_type_full = vm.get("machineType", "")
            machine_type = machine_type_full.split("/")[-1] if machine_type_full else ""
            status = vm.get("status", "UNKNOWN")
            cpu_avg_1h = get_cpu_avg(project, instance_id, minutes=60)
            cpu_avg_12h = get_cpu_avg(project, instance_id, minutes=60*12)
            cost = billing_map.get(name)
            if cost is None:
                est_hourly = estimate_cost_by_machine(machine_type)
                cost = est_hourly * 24
            total_cost += cost
            state = "Idle" if (cpu_avg_12h * 100) < cpu_threshold else "Active"
            instances_report.append({
                "name": name,
                "zone": zone,
                "status": status,
                "labels": labels,
                "machine_type": machine_type,
                "cpu_avg_1h_pct": round(cpu_avg_1h * 100, 2),
                "cpu_avg_12h_pct": round(cpu_avg_12h * 100, 2),
                "cost_24h": round(cost, 4),
                "state": state
            })

    report = {
        "project": project,
        "total_cost_24h": round(total_cost, 4),
        "instances": instances_report,
        "dry_run": dry_run
    }

    send_result = send_report_via_sendgrid(sendgrid_key, admin_email, from_email, report)
    logging.info(f"Email send result: {send_result}")

    return (json.dumps(report), 200, {"Content-Type": "application/json"})
