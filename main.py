from app import app, socketio

# For gunicorn deployment, just expose the app
if __name__ == '__main__':
    # Development server - only runs when called directly
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False, log_output=True)
