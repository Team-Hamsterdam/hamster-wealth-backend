-- cat chronicle.sql | heroku pg:psql --app hamsterwealth
CREATE TABLE IF NOT EXISTS client (
    token text unique not null,
    username text not null,
    password text not null,
    primary key (token)
);
CREATE TABLE IF NOT EXISTS portfolio (
    token text not null,
    portfolio_id int unique not null,
    title text,
    balance int,
    primary key (token, portfolio_id),
    foreign key (token) references client(token)
);
CREATE TABLE IF NOT EXISTS stock (
    portfolio_id int,
    ticker text not null,
    company text not null,
    avg_price real,
    units int,
    primary key (portfolio_id, ticker)
);