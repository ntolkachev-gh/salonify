# Salonify

A multi-tenant salon management platform with Telegram bot integration, built with Django 4.x and Django REST Framework.

## Features

- **Multi-tenant Platform**: One user can manage multiple salons
- **Telegram Bot Integration**: Each user gets their own Telegram bot for:
  - Salon registration
  - Appointment booking
  - Client notifications and reminders
  - AI-powered Q&A using OpenAI and knowledge base
- **Complete Salon Management**:
  - Masters/employees management
  - Services catalog
  - Client database
  - Appointment scheduling
  - Document management with AI embeddings
  - Social media post scheduling
- **Background Tasks**: Celery-powered reminders and notifications
- **REST API**: Full CRUD API with JWT authentication
- **Admin Interface**: Django admin with custom filters and views

## Technology Stack

- **Backend**: Django 4.2, Django REST Framework
- **Database**: PostgreSQL with PGVector for embeddings
- **Cache/Queue**: Redis + Celery
- **AI**: OpenAI API for embeddings and chat
- **Telegram**: python-telegram-bot
- **Deployment**: Docker, Heroku
- **Authentication**: JWT tokens

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ with PGVector extension
- Redis
- Docker (optional)

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/salonify.git
   cd salonify
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

5. **Set up database**
   ```bash
   # Create PostgreSQL database
   createdb salonify
   
   # Enable PGVector extension
   psql salonify -c "CREATE EXTENSION vector;"
   
   # Run migrations
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run the development server**
   ```bash
   python manage.py runserver
   ```

8. **Start Celery worker (in another terminal)**
   ```bash
   celery -A salonify worker --loglevel=info
   ```

9. **Start Celery beat (in another terminal)**
   ```bash
   celery -A salonify beat --loglevel=info
   ```

### Docker Development Setup

1. **Build and run with Docker Compose**
   ```bash
   docker-compose up --build
   ```

2. **Run migrations**
   ```bash
   docker-compose exec web python manage.py migrate
   ```

3. **Create superuser**
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

The application will be available at `http://localhost:8000`

## Configuration

### Environment Variables

Create a `.env` file based on `env.example`:

```env
# Django settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgresql://username:password@localhost:5432/salonify

# Redis
REDIS_URL=redis://localhost:6379/0

# Telegram Bot (optional - users can set their own)
TELEGRAM_BOT_TOKEN=your-telegram-bot-token-here

# OpenAI (optional - users can set their own)
OPENAI_API_KEY=your-openai-api-key-here

# Logging
DJANGO_LOG_LEVEL=INFO
```

### Database Setup

1. **PostgreSQL with PGVector**
   ```sql
   CREATE DATABASE salonify;
   \c salonify
   CREATE EXTENSION vector;
   ```

2. **Run migrations**
   ```bash
   python manage.py migrate
   ```

## API Documentation

### Authentication

The API uses JWT authentication. Obtain tokens at:
- `POST /api/auth/token/` - Get access and refresh tokens
- `POST /api/auth/token/refresh/` - Refresh access token
- `POST /api/auth/token/verify/` - Verify token

### Endpoints

- `GET /api/users/` - User management
- `GET /api/salons/` - Salon management
- `GET /api/masters/` - Master/employee management
- `GET /api/services/` - Service catalog
- `GET /api/clients/` - Client database
- `GET /api/appointments/` - Appointment scheduling
- `GET /api/documents/` - Document management
- `GET /api/posts/` - Social media posts
- `GET /api/embeddings/` - AI embeddings

### Example API Usage

```bash
# Get JWT token
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'

# Use token in requests
curl -X GET http://localhost:8000/api/salons/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Telegram Bot Setup

### Creating a Telegram Bot

1. **Talk to BotFather**
   - Start a chat with [@BotFather](https://t.me/BotFather)
   - Send `/newbot`
   - Follow the instructions to create your bot
   - Save the bot token

2. **Configure in Admin**
   - Go to Django admin
   - Edit your user profile
   - Add the Telegram bot token
   - Add OpenAI API key (optional)

3. **Bot Commands**
   - `/start` - Welcome message
   - `/help` - Show available commands
   - `/register_salon` - Register a new salon
   - `/book_appointment` - Book an appointment
   - `/my_appointments` - View appointments
   - `/cancel_appointment` - Cancel an appointment

## Deployment

### Heroku Deployment

1. **Install Heroku CLI**
   ```bash
   # Install Heroku CLI
   # https://devcenter.heroku.com/articles/heroku-cli
   ```

2. **Create Heroku app**
   ```bash
   heroku create your-app-name
   ```

3. **Add add-ons**
   ```bash
   # PostgreSQL with PGVector support
   heroku addons:create heroku-postgresql:hobby-dev
   
   # Redis
   heroku addons:create heroku-redis:hobby-dev
   ```

4. **Enable PGVector extension**
   ```bash
   heroku pg:psql -c "CREATE EXTENSION vector;"
   ```

5. **Set environment variables**
   ```bash
   heroku config:set SECRET_KEY=your-secret-key
   heroku config:set DEBUG=False
   heroku config:set ALLOWED_HOSTS=your-app-name.herokuapp.com
   heroku config:set DJANGO_LOG_LEVEL=INFO
   ```

6. **Deploy**
   ```bash
   git push heroku main
   ```

7. **Run migrations**
   ```bash
   heroku run python manage.py migrate
   ```

8. **Create superuser**
   ```bash
   heroku run python manage.py createsuperuser
   ```

9. **Scale workers**
   ```bash
   heroku ps:scale web=1 worker=1 beat=1
   ```

### Docker Deployment

1. **Build image**
   ```bash
   docker build -t salonify .
   ```

2. **Run with environment variables**
   ```bash
   docker run -d \
     -p 8000:8000 \
     -e DATABASE_URL=your-database-url \
     -e REDIS_URL=your-redis-url \
     -e SECRET_KEY=your-secret-key \
     salonify
   ```

## Development

### Project Structure

```
salonify/
├── salonify/           # Django project settings
├── core/               # Core models and business logic
├── api/                # REST API endpoints
├── telegram_bot/       # Telegram bot functionality
├── templates/          # Django templates
├── static/             # Static files
├── media/              # Uploaded files
├── requirements.txt    # Python dependencies
├── Dockerfile         # Docker configuration
├── docker-compose.yml # Docker Compose for development
├── Procfile           # Heroku process configuration
└── README.md          # This file
```

### Running Tests

```bash
python manage.py test
```

### Code Quality

```bash
# Format code
black .

# Check linting
flake8 .

# Type checking
mypy .
```

## Features in Detail

### Multi-tenant Architecture

- Each user can create and manage multiple salons
- Complete data isolation between users
- Scalable permission system

### Telegram Bot Integration

- Automated salon registration process
- Interactive appointment booking
- Smart reminders and notifications
- AI-powered customer support using OpenAI

### AI-Powered Knowledge Base

- Document upload and processing (DOCX, TXT, Google Docs)
- Automatic text embedding generation using OpenAI
- Vector similarity search for relevant information
- Contextual responses to customer questions

### Background Tasks

- Appointment reminders (1 hour before)
- Scheduled social media posts
- Document embedding generation
- Client statistics updates

### API Features

- JWT authentication
- Comprehensive CRUD operations
- Advanced filtering and search
- Pagination and ordering
- Custom permissions and validation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue on GitHub or contact the development team.

## Changelog

### v1.0.0 (Current)
- Initial release
- Multi-tenant salon management
- Telegram bot integration
- REST API
- AI-powered knowledge base
- Background task processing
- Heroku deployment support 