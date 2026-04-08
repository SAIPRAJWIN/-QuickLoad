# 🚚 QuickLoad: A Real-Time Smart Booking Platform

Welcome to the official repository for **QuickLoad**, an integrated web-based logistics management system designed to streamline transportation services by connecting customers, drivers, and administrators on a single, seamless digital platform. 

> **Tagline:** Logistics Reimagined. Mobility Simplified. The digital bridge for India's transportation network.

---

## 📑 Table of Contents
1. [Project Overview](#-project-overview)
2. [Team Details](#-team-details)
3. [Key Features](#-key-features)
4. [System Architecture](#-system-architecture)
5. [Technology Stack](#-technology-stack)
6. [Database Schema](#-database-schema)
7. [Installation & Setup](#-installation--setup)
8. [Testing & Security](#-testing--security)
9. [Future Scope](#-future-scope)
10. [Academic Details](#-academic-details)

---

## 📖 Project Overview

The rapid growth of urbanization and e-commerce has significantly increased the demand for efficient and reliable logistics and transportation services. Traditional systems rely on manual coordination, phone-based bookings, and fragmented communication, leading to delays and lack of transparency. 

**QuickLoad** addresses these challenges by offering a unified platform where:
* **Customers** can book vehicles, select pickup/drop locations, calculate accurate fares, and track shipments in real-time.
* **Driver Partners** can register, verify their documents securely, manage their trips, and track their daily earnings.
* **Administrators** have complete oversight through a centralized dashboard to monitor bookings, verify driver applications, and analyze revenue trends.

---

## 👥 Team Details

We are a team of Bachelor of Technology students specializing in Computer Science and Engineering from the **Kalasalingam Academy of Research and Education**.

### 🎓 Developers
| Name | Register Number | Role / Contribution |
| :--- | :--- | :--- |
| **Boppana Rohith** | 99220041454 | Team Lead & Implementation |
| **Bachula Yaswanth Babu** | 99220041445 | Backend Logic & Integration |
| **Anisetty Sai Prajwin** | 99220041438 | Database Design & Management |
| **Yerla Vinayasree** | 99220041423 | Frontend Development & UI/UX |

### 👨‍🏫 Project Supervisor
* **Project Supervisor:** Mr. N. R. Sathis Kumar (Assistant Professor, Dept. of CSE).
* **Project Coordinators:** Dr. T. Manikumar & Mr. N.R. Sathiskumar.
* **Head of Department:** Dr. R. Raja Subramanian.

---

## 🚀 Key Features

### 1. Customer Service Module
* **Secure Authentication:** User registration with OTP-based email verification.
* **Smart Vehicle Selection:** Choose vehicles based on load weight capacity and service category.
* **Dynamic Fare Estimation:** Automatic calculation based on distance and vehicle type.
* **Live Tracking:** Real-time shipment/trip tracking with dynamic status updates.

### 2. Driver Partner Module
* **Multi-Step Onboarding:** Structured registration capturing personal info, vehicle details, and bank account setup.
* **Document Verification:** Secure upload of Driving License, Aadhaar Card, PAN Card, and Vehicle RC in PDF format.
* **Trip Management:** Interface to accept or decline live trip requests.
* **Earnings Dashboard:** Real-time summary of daily and lifetime earnings, completed trips, and active status.

### 3. Admin Dashboard
* **Application Review:** Verify and approve/reject pending driver applications and documents.
* **Live Monitoring:** Track active trips, monitor customers, and manage assigned vehicles.
* **Revenue Analytics:** Graphical insights into booking trends, total revenue, and platform usage.

---

## 🏗 System Architecture

QuickLoad follows a highly scalable **Three-Layer Architecture**:

1. **Presentation Layer (UI):** Built with HTML5, CSS3, and JS. Handles responsive user interactions across Customer, Driver, and Admin portals.
2. **Application / Business Layer:** Powered by Python (Flask). Manages routing, booking validation, fare calculation logic, driver assignment, and real-time status updates.
3. **Data Management Layer:** Handled by MySQL. Ensures structured and relational storage of all platform data with strict normalization.

---

## 🛠 Technology Stack

### Frontend
* **HTML5 & CSS3:** Page structuring and responsive design.
* **JavaScript:** Dynamic DOM manipulation and client-side validation.

### Backend
* **Python:** Core programming language.
* **Flask Framework:** Lightweight web framework for RESTful API development and routing.

### Database
* **MySQL:** Relational database for robust, ACID-compliant data storage.
* **MySQL Connector:** For seamless Python-Database communication.

### APIs & Integrations
* **Google Maps API / OpenStreetMap:** For reverse geocoding, distance calculation, and route visualization.
* **Email Services:** For OTP generation and automated user notifications.

### Security
* **Bcrypt:** For secure, one-way password hashing.
* **Flask Sessions:** For role-based access control and session management.

---

## 🗄 Database Schema

The system utilizes a highly relational database model to maintain data integrity.

| Table Name | Primary Key | Foreign Keys | Key Attributes |
| :--- | :--- | :--- | :--- |
| **CUSTOMER** | `Customer_ID` | None | Name, Email, Phone, Address, Password |
| **DRIVER** | `Driver_ID` | None | Name, Contact, License_No, Bank_Details, Status |
| **VEHICLE** | `Vehicle_ID` | `Driver_ID` | Vehicle_Type, Registration_No, Capacity |
| **BOOKING** | `Booking_ID` | `Customer_ID`, `Driver_ID` | Pickup, Drop, Goods_Type, Distance, Fare, Status |
| **PAYMENT** | `Payment_ID` | `Booking_ID` | Payment_Method, Status, Amount, Transaction_Date |
| **ADMIN** | `Admin_ID` | None | Username, Password, Role |
