CREATE DATABASE chilli_db;

\c chilli_db;

CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    adhar VARCHAR(20) NOT NULL,
    company VARCHAR(255),
    mobile VARCHAR(20) NOT NULL,
    password TEXT NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE
);

CREATE TABLE accounts (
    acc_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id),
    fname TEXT NOT NULL,
    mname TEXT,
    lname TEXT NOT NULL,
    type TEXT,
    company_name TEXT,
    sname TEXT,
    adhar_card TEXT,
    bank TEXT NOT NULL,
    acc_no TEXT NOT NULL,
    acc_holder TEXT NOT NULL,
    ifsc TEXT NOT NULL,
    gst TEXT,
    address TEXT NOT NULL,
    mobile TEXT NOT NULL,
    email TEXT
);

CREATE TABLE cities (
    city_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id),
    city TEXT,
    district TEXT,
    state TEXT,
    pincode TEXT
);

CREATE TABLE heads (
    head_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id),
    head_name TEXT
);

CREATE TABLE lots (
    lot_no SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id),
    date DATE,
    city TEXT,
    adhar_card TEXT,
    farmer_name TEXT,
    no_of_bags INT
);

CREATE TABLE rates (
    rate_id SERIAL PRIMARY KEY,
    lot_no INT REFERENCES lots(lot_no),
    city TEXT,
    farmer_name TEXT,
    no_of_bags INT,
    rate NUMERIC,
    purchaser TEXT
);

CREATE TABLE billing (
    bill_id SERIAL PRIMARY KEY,
    lot_no INT REFERENCES lots(lot_no),
    bag_no INT,
    weight NUMERIC,
    total_weight NUMERIC,
    commission NUMERIC,
    amount NUMERIC,
    date DATE
);
