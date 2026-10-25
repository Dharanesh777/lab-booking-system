# Lab Slots: Frontend

React + Vite. Talks to the FastAPI backend in `/backend`.

## Run
```
cp .env.example .env     # set VITE_API_URL if the backend is not on :8000
npm install
npm run dev              # http://localhost:5173
```
Start the backend first: `cd backend && uvicorn app.main:app --reload`

## Pages
Student: `/book`, `/my-bookings`
Admin: `/admin/approvals`, `/admin/block`, `/admin/labs`, `/admin/admins`
