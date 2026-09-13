Air Ticket Reservation System

A full-stack flight booking system built with Flask and MySQL, supporting three distinct user roles — customers, booking agents, and airline staff — each with their own permissions and views.

Overview

This project simulates a real airline reservation platform, covering the full flow from account registration and flight search to booking and staff-side analytics. The relational schema spans 15 interconnected tables, modeling entities like customers, flights, tickets, purchases, airports, and staff permissions.

Features
Role-based access control — separate registration and login flows for customers, booking agents, and airline staff, with staff/agent registration gated behind an authorization key
Flight search — search by departure/arrival airport (including city aliases) and date, with live status (upcoming, in-progress, delayed, completed)
Booking — customers and agents can book flights, with double-booking prevention
Staff dashboard — filterable flight views by date range and airport, passenger manifests per flight
Admin analytics — top booking agents by tickets sold and commission, most frequent customers, monthly ticket sales, on-time vs. delayed performance, and top destinations by time window
Secure authentication — passwords hashed with Werkzeug's generate_password_hash / check_password_hash
Tech Stack
Backend: Python, Flask
Database: MySQL
Frontend: HTML/CSS (Jinja templates)
Database

The schema (air_ticket_reservation_create_tabels.sql) includes 15 interconnected tables covering customers, booking agents, airline staff and permissions, flights, airports and city aliases, tickets, and purchases.

Setup
1. Clone the repo and install dependencies:
   pip install flask mysql-connector-python werkzeug
2. Create the MySQL database and run air_ticket_reservation_create_tabels.sql to set up the tables.
3. Set your database credentials as environment variables (or update the connection block in airticket.py).
4. Run the app:
   python airticket.py

   
Project Context
Built as a course project for a Databases class, focused on designing a normalized relational schema for a real-world multi-role system and implementing the full application layer on top of it.
