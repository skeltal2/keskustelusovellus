CREATE TABLE users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT,
        admin INT
    );

CREATE TABLE boards (
        id SERIAL PRIMARY KEY,
        title TEXT,
        hidden INT
    );

CREATE TABLE threads (
        id SERIAL PRIMARY KEY,
        title TEXT,
        content TEXT,
        user_id INT REFERENCES users (id),
        board_id INT REFERENCES boards (id),
        created_at TIMESTAMP,
        hidden INT
    );

CREATE TABLE messages (
        id SERIAL PRIMARY KEY,
        content TEXT,
        user_id INT REFERENCES users (id),
        thread_id INT REFERENCES threads (id),
        created_at TIMESTAMP,
        hidden INT
    );