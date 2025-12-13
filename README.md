# LDN Portal - Flask Backend

Flask REST API backend for the LDN Portal application, built according to the database schema specification.

## Features

- **User Management**: Authentication with AWS Cognito, role-based access control (Admin, Clerk, Agent)
- **Job Management**: Complete job lifecycle from creation to completion with logistics tracking
- **Property Management**: Property data synced from InventoryBase API
- **Chat System**: Real-time chat per job with read/unread tracking
- **Notifications**: Multi-channel notifications (in-app, email, SMS) with delivery tracking
- **Availability Management**: Clerk availability calendar for future date scheduling
- **Invoice Tracking**: Clerk invoice submission and tracking system
- **Auto-Assignment**: Location-based job assignment engine (to be implemented)

## Project Structure

```
ldn_backend/
├── app/
│   ├── __init__.py          # Application factory
│   ├── models/              # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── property.py
│   │   ├── job.py
│   │   ├── chat.py
│   │   ├── notification.py
│   │   ├── invoice.py
│   │   ├── availability.py
│   │   ├── integration.py
│   │   └── assignment_log.py
│   └── routes/              # API routes/blueprints
│       ├── __init__.py
│       ├── auth.py
│       ├── users.py
│       ├── jobs.py
│       ├── properties.py
│       ├── chat.py
│       ├── notifications.py
│       ├── invoices.py
│       └── availability.py
├── config.py                # Configuration classes
├── run.py                   # Application entry point
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variables template
└── README.md               # This file
```

## Setup Instructions

### 1. Prerequisites

- Python 3.9+
- PostgreSQL 12+
- pip (Python package manager)

### 2. Install Dependencies

```bash
cd ldn_backend
pip install -r requirements.txt
```

### 3. Database Setup

1. Create a PostgreSQL database:
```sql
CREATE DATABASE ldn_portal;
```

2. Run the database schema SQL file:
```bash
psql -U postgres -d ldn_portal -f ../database_schema.sql
```

Alternatively, you can use Flask-Migrate to create the database schema:
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 4. Environment Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` and fill in your configuration:
   - Database connection string
   - AWS Cognito credentials
   - InventoryBase API credentials
   - Secret keys

### 5. Run the Application

```bash
python run.py
```

The API will be available at `http://localhost:5000`

## API Endpoints

### Authentication
- `POST /api/auth/verify` - Verify Cognito token
- `POST /api/auth/login` - Login (handled by Cognito)
- `POST /api/auth/logout` - Logout

### Users
- `GET /api/users/` - Get all users (admin only)
- `GET /api/users/<user_id>` - Get user by ID
- `PUT /api/users/<user_id>` - Update user
- `GET /api/users/me` - Get current user
- `PUT /api/users/<user_id>/location` - Update user location

### Jobs
- `GET /api/jobs/` - Get all jobs (with filters)
- `GET /api/jobs/<job_id>` - Get job by ID
- `POST /api/jobs/` - Create job (admin/agent)
- `PUT /api/jobs/<job_id>` - Update job
- `POST /api/jobs/<job_id>/assign` - Assign job to clerk (admin)
- `POST /api/jobs/<job_id>/start` - Start job (clerk)
- `POST /api/jobs/<job_id>/check-in` - Check in at property (clerk)
- `POST /api/jobs/<job_id>/complete` - Complete job (clerk)

### Properties
- `GET /api/properties/` - Get all properties
- `GET /api/properties/<property_id>` - Get property by ID
- `POST /api/properties/` - Create property
- `PUT /api/properties/<property_id>` - Update property
- `POST /api/properties/sync` - Sync from InventoryBase

### Chat
- `GET /api/chat/jobs/<job_id>/messages` - Get messages
- `POST /api/chat/jobs/<job_id>/messages` - Send message
- `POST /api/chat/jobs/<job_id>/read` - Mark as read
- `GET /api/chat/jobs/<job_id>/unread-count` - Get unread count

### Notifications
- `GET /api/notifications/` - Get notifications
- `PUT /api/notifications/<notification_id>/read` - Mark as read
- `PUT /api/notifications/read-all` - Mark all as read
- `GET /api/notifications/unread-count` - Get unread count

### Invoices
- `GET /api/invoices/` - Get invoices
- `POST /api/invoices/` - Submit invoice (clerk)
- `PUT /api/invoices/<invoice_id>` - Update invoice status (admin)
- `GET /api/invoices/check-submission` - Check if submitted

### Availability
- `GET /api/availability/` - Get availability records
- `POST /api/availability/` - Create availability
- `PUT /api/availability/<availability_id>` - Update availability
- `DELETE /api/availability/<availability_id>` - Delete availability

## Database Models

All models are based on the `database_schema.sql` specification:

- **User**: Authentication, roles, location tracking
- **Property**: Property data from InventoryBase
- **Job**: Job lifecycle and logistics tracking
- **ChatMessage**: Job-specific chat messages
- **ChatParticipant**: Read/unread tracking
- **Notification**: Multi-channel notifications
- **ClerkInvoice**: Invoice submission tracking
- **ClerkAvailability**: Future availability calendar
- **IntegrationSettings**: OAuth tokens for InventoryBase
- **AssignmentLog**: Audit log for job assignments

## Authentication

The application uses AWS Cognito for authentication. Token verification needs to be implemented in the `auth.py` routes. The current implementation has placeholder decorators that need to be completed with actual Cognito token validation.

## Development

### Running Migrations

```bash
# Initialize migrations (first time only)
flask db init

# Create a new migration
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade

# Rollback last migration
flask db downgrade
```

### Code Style

Follow PEP 8 style guidelines. Consider using:
- `black` for code formatting
- `flake8` for linting
- `pytest` for testing

## TODO / Future Enhancements

- [ ] Implement AWS Cognito token validation
- [ ] Implement auto-assignment engine (location-based matching)
- [ ] Implement InventoryBase API sync
- [ ] Add file upload handling for attachments
- [ ] Add distance calculation for location warnings
- [ ] Add comprehensive error handling
- [ ] Add request validation
- [ ] Add unit and integration tests
- [ ] Add API documentation (Swagger/OpenAPI)
- [ ] Add logging and monitoring
- [ ] Add rate limiting
- [ ] Add caching layer

## License

Proprietary - LDN Portal

