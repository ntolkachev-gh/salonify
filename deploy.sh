#!/bin/bash

# Salonify Heroku Deployment Script

echo "🚀 Starting Salonify deployment to Heroku..."

# Check if Heroku CLI is installed
if ! command -v heroku &> /dev/null; then
    echo "❌ Heroku CLI is not installed. Please install it first."
    echo "Visit: https://devcenter.heroku.com/articles/heroku-cli"
    exit 1
fi

# Check if user is logged in to Heroku
if ! heroku auth:whoami &> /dev/null; then
    echo "❌ You are not logged in to Heroku. Please run 'heroku login' first."
    exit 1
fi

# Get app name from user or use default
read -p "Enter your Heroku app name (or press Enter for 'salonify-app'): " APP_NAME
APP_NAME=${APP_NAME:-salonify-app}

echo "📱 Creating Heroku app: $APP_NAME"

# Create Heroku app
heroku create $APP_NAME

# Add PostgreSQL addon
echo "🐘 Adding PostgreSQL addon..."
heroku addons:create heroku-postgresql:hobby-dev --app $APP_NAME

# Add Redis addon
echo "🔴 Adding Redis addon..."
heroku addons:create heroku-redis:hobby-dev --app $APP_NAME

# Set environment variables
echo "⚙️  Setting environment variables..."
heroku config:set DEBUG=False --app $APP_NAME
heroku config:set DJANGO_LOG_LEVEL=INFO --app $APP_NAME
heroku config:set ALLOWED_HOSTS=$APP_NAME.herokuapp.com --app $APP_NAME

# Generate secret key
SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
heroku config:set SECRET_KEY="$SECRET_KEY" --app $APP_NAME

# Enable PGVector extension
echo "🔧 Enabling PGVector extension..."
heroku pg:psql --app $APP_NAME -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Deploy to Heroku
echo "🚀 Deploying to Heroku..."
git push heroku main

# Run migrations
echo "🔄 Running migrations..."
heroku run python manage.py migrate --app $APP_NAME

# Create superuser (optional)
read -p "Do you want to create a superuser? (y/N): " CREATE_SUPERUSER
if [[ $CREATE_SUPERUSER =~ ^[Yy]$ ]]; then
    echo "👤 Creating superuser..."
    heroku run python manage.py createsuperuser --app $APP_NAME
fi

# Scale workers
echo "⚡ Scaling workers..."
heroku ps:scale web=1 worker=1 beat=1 --app $APP_NAME

echo "✅ Deployment completed successfully!"
echo "🌐 Your app is available at: https://$APP_NAME.herokuapp.com"
echo "🔧 Admin panel: https://$APP_NAME.herokuapp.com/admin/"
echo "📚 API documentation: https://$APP_NAME.herokuapp.com/api/"

echo ""
echo "📝 Next steps:"
echo "1. Visit the admin panel and configure your user profile"
echo "2. Add your Telegram bot token and OpenAI API key"
echo "3. Create your first salon"
echo "4. Test the Telegram bot functionality"

echo ""
echo "🎉 Happy coding with Salonify!" 