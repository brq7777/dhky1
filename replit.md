# Real-Time Financial Assets Dashboard

## Overview

This is a real-time financial assets monitoring dashboard that tracks prices for cryptocurrencies, precious metals, and forex pairs. The application provides live price updates, price alert functionality, and a responsive Arabic-language interface. It fetches data from multiple financial APIs (Binance for crypto and TwelveData for metals/forex) and delivers real-time updates to users through WebSocket connections.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Technology Stack**: Vanilla JavaScript with Socket.IO client for real-time communication
- **UI Framework**: Custom CSS with RTL (right-to-left) support for Arabic language
- **Real-time Updates**: WebSocket-based communication for live price feeds
- **State Management**: Browser localStorage for persisting alert configurations
- **Responsive Design**: Grid-based layout that adapts to different screen sizes

### Backend Architecture
- **Web Framework**: Flask with Flask-SocketIO for WebSocket support
- **API Service Layer**: Centralized PriceService class handling multiple data sources
- **Real-time Communication**: Socket.IO for bidirectional client-server communication
- **Error Handling**: Comprehensive logging and graceful error recovery
- **Modular Design**: Separation of concerns with dedicated service classes

### Data Flow
- **Price Fetching**: Periodic API calls to external services with caching mechanism
- **Real-time Broadcasting**: Server pushes price updates to all connected clients
- **Alert System**: Server-side alert monitoring with client notifications
- **Client-Server Sync**: Bidirectional communication for alert management

### Asset Management
- **Multi-Source Data**: Integration with both Binance (crypto) and TwelveData (metals/forex) APIs
- **Asset Categories**: Organized grouping of cryptocurrencies, metals, and forex pairs
- **Localization**: Arabic asset names and RTL interface support

## External Dependencies

### Financial Data APIs
- **Binance API**: Real-time cryptocurrency prices (BTCUSDT, ETHUSDT)
  - Base URL: `https://api.binance.com/api/v3`
  - No authentication required for public price data
- **TwelveData API**: Precious metals and forex data (XAU/USD, EUR/USD, GBP/USD)
  - Base URL: `https://api.twelvedata.com`
  - API Key: Environment variable `TWELVE_DATA_API_KEY`

### Third-Party Libraries
- **Flask**: Web application framework
- **Flask-SocketIO**: Real-time WebSocket communication
- **Socket.IO**: Client-side real-time communication library
- **Requests**: HTTP client for API calls

### Environment Configuration
- **SESSION_SECRET**: Flask session security key
- **TWELVE_DATA_API_KEY**: API authentication for TwelveData service

### Browser Dependencies
- **Socket.IO CDN**: Real-time communication client library
- **Web Audio API**: For alert sound notifications
- **LocalStorage**: Client-side alert state persistence