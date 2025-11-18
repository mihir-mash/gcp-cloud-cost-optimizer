GCP Cloud Cost Analyzer and Idle VM Auto-Shutdown

This project is a fully automated cloud cost-optimization system built using Google Cloud Platform (GCP). It analyzes virtual machine usage, calculates daily cloud costs, identifies idle resources, and automatically shuts down underutilized VMs. The solution uses serverless components, making it efficient, scalable, and ideal for DevOps automation.

🚀 Project Overview

The system is built with two Cloud Functions:

1. Cost Analyzer Function

Reads Billing Export data from BigQuery

Lists all running Compute Engine VMs

Fetches CPU metrics using Cloud Monitoring

Calculates or estimates 24-hour VM cost

Classifies VMs as Active, Low-Usage, or Idle

Sends a daily email report using SendGrid

2. Idle VM Auto-Shutdown Function

Checks CPU utilization across all VMs

Identifies idle VMs (CPU usage < 5 percent)

Automatically stops VMs labeled with:

auto-shutdown=true


Logs shutdown events

Supports DRY_RUN mode for safe testing

Both functions run automatically using Cloud Scheduler, creating a fully hands-off system.

🧰 Tech Stack

Google Cloud Functions (Python)

Cloud Scheduler

Compute Engine API

Cloud Monitoring API

BigQuery Billing Export

SendGrid Email API

IAM for secure permissions

📌 Features

Automated VM cost analysis

Daily email reports

Idle VM detection

Auto shutdown with safety labels

Works across all zones

Low operational cost (serverless)

Easy to deploy and maintain

🛠️ Architecture Flow

Cloud Scheduler triggers functions daily

Cost Analyzer collects usage + cost

Email is sent using SendGrid

Idle Shutdown checks CPU usage

Idle VMs (with proper label) are stopped

📂 Project Structure
/cost_analyzer
    main.py
    requirements.txt

/idle_shutdown
    main.py
    requirements.txt

README.md

📸 Demo Outputs

Daily Email Cost Report

Idle VM Auto-Shutdown Log

Curl testing outputs

(You can add screenshots of your email and Cloud Logs here.)

📈 Future Improvements

Auto-start based on schedules

Slack/Teams notifications

Cost forecasting

Dashboard visualization in Looker Studio
