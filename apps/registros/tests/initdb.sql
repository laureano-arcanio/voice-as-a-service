-- Solo para el Postgres de prueba (compose.test.yaml).
CREATE ROLE registros LOGIN PASSWORD 'test' NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE DATABASE registros OWNER registros;
