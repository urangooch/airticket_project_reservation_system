CREATE TABLE Airline( 
    name varchar(50) PRIMARY KEY);

CREATE TABLE City( 
    name varchar(50) PRIMARY KEY);

CREATE TABLE airport( 
    name varchar(50) PRIMARY KEY, 
    city_name varchar(50) NOT NULL, 
    FOREIGN KEY (city_name) REFERENCES City(name) ON DELETE RESTRICT);

CREATE TABLE City_alias( 
    alias_name varchar(50) PRIMARY KEY, 
    city_name varchar(50) NOT NULL, 
    FOREIGN KEY (city_name) REFERENCES City(name) ON DELETE CASCADE);

CREATE TABLE airplane( 
    id INT NOT NULL, 
    airline_name varchar(50) NOT NULL, 
    seat_capacity INT NOT NULL CHECK (seat_capacity > 0), 
    PRIMARY KEY(airline_name, id), 
    FOREIGN KEY(airline_name) REFERENCES airline(name) ON DELETE CASCADE);

CREATE TABLE Flight( 
    flight_num varchar(20) NOT NULL, 
    airline_name varchar(50) NOT NULL, 
    departure_time DATETIME NOT NULL,
    arrival_time DATETIME NOT NULL, 
    price DECIMAL(10,2) NOT NULL CHECK(price >= 0), 
    status VARCHAR(20) NOT NULL, 
    departure_airport VARCHAR(50) NOT NULL, 
    arrival_airport VARCHAR(50) NOT NULL, 
    airplane_id INT NOT NULL, 
    PRIMARY KEY(airline_name, flight_num), 
    FOREIGN KEY(airline_name) REFERENCES airline(name) ON DELETE CASCADE, 
    FOREIGN KEY(departure_airport) REFERENCES airport(name) ON DELETE RESTRICT, 
    FOREIGN KEY(arrival_airport) REFERENCES airport(name) ON DELETE RESTRICT, 
    FOREIGN KEY(airline_name, airplane_id) REFERENCES airplane(airline_name, id) ON DELETE RESTRICT, 
    CHECK(status IN ('upcoming', 'in-progress', 'delayed')));

create table airline_staff( 
    username varchar(50) primary key, 
    password varchar(100) not null, 
    first_name varchar(50) not null, 
    last_name varchar(50) not null, 
    date_of_birth date not null, 
    airline_name varchar(50) not null, 
    foreign key(airline_name) REFERENCES airline(name) on delete cascade);

create table staff_permission( 
    staff_username varchar(50) not null, 
    permission varchar(50) not null, 
    primary key(staff_username, permission), 
    foreign key(staff_username) references airline_staff(username) on delete cascade, 
    CHECK (permission in('admin', 'operator')));
    
create table booking_agent( 
    email varchar(50) primary key, 
    password varchar(100) not null);

create table customer( 
    email varchar(50) primary key, 
    name varchar(200) not null, 
    password varchar(100) not null, 
    building_number varchar(20), 
    street varchar(100), 
    city varchar(50), 
    state varchar(50), 
    phone_number varchar(20), 
    passport_number varchar(50) unique not null, 
    passport_expiration_date date not null, 
    passport_country varchar(100) not null, 
    date_of_birth date not null);

create table ticket( 
    ticket_id int primary key, 
    airline_name varchar(50) not null, 
    flight_num varchar(30) not null, 
    foreign key(airline_name, flight_num) references flight(airline_name, flight_num) on delete cascade);

create table authorized_by( 
    booking_agent_email varchar(50) not null, 
    airline_name varchar(50) not null, 
    primary key(booking_agent_email, airline_name), 
    foreign key(booking_agent_email) references booking_agent(email) on delete cascade, 
    foreign key(airline_name) REFERENCES airline(name) on delete cascade);

create table purchases( 
    customer_email varchar(50) not null, 
    booking_agent_email varchar(50), 
    ticket_id INT not null, 
    purchase_date date not null, 
    primary key(customer_email, ticket_id), 
    foreign key(customer_email) references customer(email) on delete cascade, 
    foreign key(booking_agent_email) references booking_agent(email) on delete set null, 
    foreign key(ticket_id) references ticket(ticket_id) on delete cascade);
