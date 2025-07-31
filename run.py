from app import app, db
from app.models import User, Laptop

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Laptop': Laptop}

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)