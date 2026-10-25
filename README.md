# lab-booking-system

Lab Booking and Management System

A web-based lab booking and management system that allows PSG students to request laboratory slots in the AI Wing(SCPS,3AI and AIR) and administrators to manage bookings, approve or reject requests, and schedule lab reservations. The system uses FastAPI for backend APIs, MongoDB for data storage, and email notifications to keep students and administrators informed about booking updates.

## To run backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## To run frontend
```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```