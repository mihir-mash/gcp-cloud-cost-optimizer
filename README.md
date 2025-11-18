# 🌥️ GCP Cloud Cost Analyzer & Idle VM Auto-Shutdown

This project is a fully automated cloud cost-optimization system built on **Google Cloud Platform (GCP)**. It analyzes VM usage, calculates daily spending, identifies idle resources, and automatically shuts down underutilized virtual machines. The solution uses a 100 percent serverless architecture designed for efficiency, scalability, and clean DevOps automation.

## 🚀 Project Overview

The system is powered by **two Google Cloud Functions** working together:

### 🔍 Cost Analyzer Function  
- Reads Billing Export data from BigQuery  
- Lists active Compute Engine VMs across all zones  
- Fetches CPU utilization from Cloud Monitoring  
- Calculates daily cost (actual or estimated)  
- Classifies VMs as **Active / Low-Usage / Idle**  
- Sends an email report using SendGrid  
- Helps track unnecessary cloud spending each day  

### 📴 Idle VM Auto-Shutdown Function  
- Checks CPU usage from the past 1–12 hours  
- Detects idle VMs (CPU below 5 percent)  
- Automatically shuts down only VMs labeled:  

auto-shutdown=true

- Supports **DRY_RUN mode** for safe testing  
- Logs all shutdown actions to Cloud Logging  

Both functions run automatically using **Cloud Scheduler**, making the system completely hands-free.

## 🧰 Tech Stack  
- Google Cloud Functions (Python)  
- Cloud Scheduler  
- Cloud Billing Export → BigQuery  
- Compute Engine API  
- Cloud Monitoring API  
- SendGrid Email API  
- IAM Roles  

## 🌟 Features  
- Automated VM usage analysis  
- Daily email cost reports  
- Idle VM detection  
- Auto shutdown of unused instances  
- Label-based safety control  
- Cross-zone support  
- Zero-maintenance serverless design  

## 📸 Demo Outputs (add screenshots)  
- Daily cost report email  
- Idle VM shutdown log  
- Curl test output  
- Cloud Logging entries  

## 📈 Future Improvements  
- Slack or Teams notifications  
- Auto-start schedules  
- Cost forecasting  
- Looker Studio dashboard  
