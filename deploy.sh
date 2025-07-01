#!/bin/bash

# deploy.sh - Deployment script for WebSocket Chat App
# Usage: ./deploy.sh [development|production|stop|logs]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
}

# Development deployment
deploy_development() {
    log_info "Deploying WebSocket Chat App in DEVELOPMENT mode..."
    
    # Stop existing containers
    docker-compose down 2>/dev/null || true
    
    # Build and start services
    docker-compose up --build -d
    
    log_success "Development deployment completed!"
    log_info "Application available at: http://localhost:8000"
    log_info "To view logs: ./deploy.sh logs"
    log_info "To stop: ./deploy.sh stop"
}

# Production deployment
deploy_production() {
    log_info "Deploying WebSocket Chat App in PRODUCTION mode..."
    
    # Check if .env file exists
    if [ ! -f .env ]; then
        log_warning "Creating .env file with default values..."
        cat > .env << EOF
POSTGRES_DB=chatdb
POSTGRES_USER=postgres
POSTGRES_PASSWORD=chatapp123
ENVIRONMENT=production
EOF
        log_warning "Please update .env file with secure passwords before production use!"
    fi
    
    # Stop existing containers
    docker-compose -f docker-compose.prod.yml down 2>/dev/null || true
    
    # Build and start services
    docker-compose -f docker-compose.prod.yml up --build -d
    
    # Wait for services to be ready
    log_info "Waiting for services to start..."
    sleep 10
    
    # Check if services are healthy
    if docker-compose -f docker-compose.prod.yml ps | grep -q "unhealthy"; then
        log_error "Some services are unhealthy. Check logs with: ./deploy.sh logs production"
        exit 1
    fi
    
    log_success "Production deployment completed!"
    log_info "Application available at: http://localhost:80"
    log_info "Database: PostgreSQL"
    log_info "To view logs: ./deploy.sh logs production"
    log_info "To stop: ./deploy.sh stop production"
}

# Stop services
stop_services() {
    local mode=${1:-development}
    
    log_info "Stopping WebSocket Chat App ($mode mode)..."
    
    if [ "$mode" = "production" ]; then
        docker-compose -f docker-compose.prod.yml down
    else
        docker-compose down
    fi
    
    log_success "Services stopped!"
}

# View logs
view_logs() {
    local mode=${1:-development}
    
    log_info "Viewing logs ($mode mode)..."
    
    if [ "$mode" = "production" ]; then
        docker-compose -f docker-compose.prod.yml logs -f
    else
        docker-compose logs -f
    fi
}

# Backup database
backup_database() {
    log_info "Creating database backup..."
    
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local backup_file="backup_${timestamp}.sql"
    
    # For SQLite (development)
    if [ -f "./data/chat.db" ]; then
        cp "./data/chat.db" "./backup_${timestamp}.db"
        log_success "SQLite backup created: backup_${timestamp}.db"
    fi
    
    # For PostgreSQL (production)
    if docker-compose -f docker-compose.prod.yml ps | grep -q "db"; then
        docker-compose -f docker-compose.prod.yml exec db pg_dump -U postgres chatdb > "$backup_file"
        log_success "PostgreSQL backup created: $backup_file"
    fi
}

# Show help
show_help() {
    echo "WebSocket Chat App Deployment Script"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  development    Deploy in development mode (SQLite, hot reload)"
    echo "  production     Deploy in production mode (PostgreSQL, Nginx)"
    echo "  stop [mode]    Stop services (development|production)"
    echo "  logs [mode]    View logs (development|production)"
    echo "  backup         Create database backup"
    echo "  clean          Remove all containers and volumes"
    echo "  help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 development"
    echo "  $0 production"
    echo "  $0 stop production"
    echo "  $0 logs development"
    echo ""
}

# Clean up everything
cleanup() {
    log_warning "This will remove ALL containers, images, and volumes!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Cleaning up..."
        
        # Stop all services
        docker-compose down -v 2>/dev/null || true
        docker-compose -f docker-compose.prod.yml down -v 2>/dev/null || true
        
        # Remove images
        docker rmi $(docker images "websocket-chat*" -q) 2>/dev/null || true
        
        # Remove volumes
        docker volume prune -f
        
        log_success "Cleanup completed!"
    else
        log_info "Cleanup cancelled."
    fi
}

# Main script
main() {
    # Check prerequisites
    check_docker
    
    # Parse command
    case "${1:-help}" in
        "development"|"dev")
            deploy_development
            ;;
        "production"|"prod")
            deploy_production
            ;;
        "stop")
            stop_services "$2"
            ;;
        "logs")
            view_logs "$2"
            ;;
        "backup")
            backup_database
            ;;
        "clean")
            cleanup
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            log_error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"