CREATE TABLE IF NOT EXISTS client (
    token text unique not null,
    name text not null,
    primary kEY (token)
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
UPDATE portfolio
                SET  portfolio.balance = 500
                WHERE portfolio.token like "eyJhbGciOiJSUzI1NiIsImtpZCI6ImUxYWMzOWI2Y2NlZGEzM2NjOGNhNDNlOWNiYzE0ZjY2ZmFiODVhNGMiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJhY2NvdW50cy5nb29nbGUuY29tIiwiYXpwIjoiOTEyNTczNTYzNTU4LWdpbTAwb28wZDVmMzR1aTdtNzhqMXEydmxkaXZxcnZkLmFwcHMuZ29vZ2xldXNlcmNvbnRlbnQuY29tIiwiYXVkIjoiOTEyNTczNTYzNTU4LWdpbTAwb28wZDVmMzR1aTdtNzhqMXEydmxkaXZxcnZkLmFwcHMuZ29vZ2xldXNlcmNvbnRlbnQuY29tIiwic3ViIjoiMTEwMTcxNjM0MjEzMDkxMzcxOTYwIiwiZW1haWwiOiJqb25ueXNtaXRoMjE2MjE2QGdtYWlsLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJhdF9oYXNoIjoiNEMwcFNVcnFWbkxjRUg4TG92cjhFdyIsIm5vbmNlIjoiZ0VMT0RMMGtHcXBMWEZ4TDFyTjYiLCJpYXQiOjE2MTgwMzMxMTMsImV4cCI6MTYxODAzNjcxM30.Pw4hYQrIa39locbdfv1neG00wROaSEmAJyl2JOk1k4xomzGe3QAwEDqTmyuMCC4CoYMGpSJi9ArfSEu_npfefoG9gwiqL6LZy8p-ddWUf3U1IltO-CHkG0vsfQI2NX2hmxbZ_6lXcd3egTRTOZ4Vg5usz7cRkuWjKBMSORNshveJP4ohocq-JxMqTMJvqGCr4RTFe5JvXTzo-Hc560U5HEP1Pc7RylUiz1FgNXuNV8-ttEbL7g3_5A1uVpGSWtKdgaHtQ5PV2QFt0h3D7E-yCGYhjSH2jCk2irWQetf2cYIZNKI1GCt0PMzM-2oSXvv_wrr0OWwc6exXRvhifxS0ow" and portfolio.portfolio_id like 1;