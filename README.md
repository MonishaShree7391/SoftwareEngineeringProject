
# Sirantha RechnungSplit 🧾

![Sirantha RechnungSplit Logo](Microservices/frontend_ui/static/images/LOGO_SiranthaRechnunSplit.jpg)


A modern, microservices-based web application for splitting grocery bills with roommates, friends, or groups—designed for real-world use with invoices from REWE, Kaufland, and more.

---

##  🧩Overview

**Sirantha RechnungSplit** simplifies shared grocery expense tracking by enabling users to upload PDF invoices, extract itemized data via OCR, and split costs between registered and non-registered users. It supports debt tracking, full/partial settlements, and admin-level user control—all backed by a scalable microservices architecture deployed on **Microsoft Azure**.

**Access to LIVE application:**
https://frontend-ui.victoriousriver-e1350c51.westus2.azurecontainerapps.io/login
if admin: https://frontend-ui.victoriousriver-e1350c51.westus2.azurecontainerapps.io/admin_dashboard.html

---

## 🧩 Microservices Architecture

The system is decomposed into the following services:

- **AuthService** – Handles user registration, login, JWT auth, and profile/password management
- **InvoiceService** – Processes uploaded PDF invoices via EasyOCR and regex parsing
- **SplitService** – Manages bill splitting and cost distribution among participants
- **DebtService** – Tracks real-time balances and records settlements
- **AdminService** – Enables privileged actions (user role control, system-level views)
- **Frontend_UI** – Flask-based web UI for user interaction

Each service is containerized using Docker and deployed via **Azure Container Apps**, communicating securely through REST APIs.

---

## 🧩 Tech Stack

| Layer | Technologies |
|-------|--------------|
| Backend | Flask, SQLAlchemy, Flask-JWT-Extended |
| OCR & Parsing | EasyOCR, PyMuPDF, Regex, Pandas |
| Frontend | HTML, CSS, Bootstrap, Jinja2 |
| Database | Microsoft SQL Server (shared) |
| Authentication | JWT, bcrypt |
| Cloud Hosting | Azure Container Apps, Azure Key Vault |
| CI/CD (optional) | GitHub Actions |

---

## 🧩 Security

- JWT-based stateless authentication
- Passwords hashed using bcrypt (12+ rounds)
- Role-based route protection for admin actions
- Input validation & sanitization on all endpoints
- Secrets managed via Azure Key Vault & container environment variables

---

## 🧩 Installation (Local Dev)

> _Note: This project is already containerized for cloud deployment. Below is for local development:_

1. Clone the repo:
   ```bash
   git clone https://github.com/yourusername/SiranthaRechnungSplit.git
   cd SiranthaRechnungSplit
   ```

2. Create a `.env` file with your database and secret config.

3. Build & run all services using Docker Compose:
   ```bash
   docker-compose up --build
   ```

4. Visit the app at `http://localhost:5000` 

---

## 🧩 Sample Features

- Upload invoices in PDF (REWE, Kaufland)
- Extract itemized data via OCR
- Assign costs to registered & custom users
- Split bills equally or item-wise
- View real-time debts ("you owe" / "owed to you")
- Full & partial settlements (UPI, cash, notes)
- Admin panel with user control and settlement logs

---

## 🧩 Testing

- Unit testing with `pytest` and `unittest`
- Integration testing across services:
  - Upload → Parse → Split → Settle
- Security testing: JWT route access, admin protection, input sanitization

---

## 🧩 Glossary

| Term | Meaning |
|------|---------|
| OCR | Optical Character Recognition for extracting text from PDFs |
| JWT | JSON Web Token used for stateless user authentication |
| Partial Settlement | Repayment covering a portion of total owed |
| SplitInvoiceDetail | Internal record of item-level split assignments |
| DebtSummary | Summary of user-to-user balances |
| Container App | Azure-hosted containerized microservice |

---

## 🧩 Future Enhancements

- Migrate frontend to React or Vue (SPA)
- Add centralized logging & monitoring via Azure Monitor or Grafana
- Implement retry logic & circuit breakers via API Gateway

---

## 🧩 License

This project is licensed under the [MIT License](LICENSE).

---

## 👥 Contributors

- Monisha Shree Senthil Nathan
