"""Create BeanBench's SQLite database and load the coffee scoring criteria."""
import db

if __name__ == "__main__":
    db.initialize_db()
    print(f"BeanBench database ready: {db.DB_PATH}")
