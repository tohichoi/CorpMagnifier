BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "Corporation" (
	"id"	INTEGER NOT NULL UNIQUE,
	"name"	TEXT,
	"sector"	INTEGER,
	"description"	TEXT,
	FOREIGN KEY("sector") REFERENCES "Sector"("id"),
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "Market" (
	"id"	INTEGER UNIQUE,
	"name"	TEXT NOT NULL UNIQUE,
	"description"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "Sector" (
	"id"	INTEGER,
	"code"	INTEGER NOT NULL UNIQUE,
	"name"	TEXT NOT NULL,
	PRIMARY KEY("id")
);
CREATE TABLE IF NOT EXISTS "StockCode" (
	"id"	INTEGER,
	"market"	INTEGER NOT NULL,
	"code"	TEXT NOT NULL UNIQUE,
	"corporation"	INTEGER NOT NULL,
	"description"	TEXT,
	FOREIGN KEY("market") REFERENCES "Market"("id"),
	FOREIGN KEY("corporation") REFERENCES "Corporation"("id"),
	PRIMARY KEY("id")
);
CREATE TABLE IF NOT EXISTS "ReportItem" (
	"id"	INTEGER,
	"currency"	TEXT,
	"account_code"	TEXT,
	"account_name"	TEXT,
	"amount"	INTEGER,
	"description"	TEXT,
	"report"	INTEGER,
	FOREIGN KEY("report") REFERENCES "Report"("id"),
	PRIMARY KEY("id")
);
CREATE TABLE IF NOT EXISTS "ReportType" (
	"id"	INTEGER,
	"name"	TEXT,
	"description"	TEXT,
	PRIMARY KEY("id")
);
CREATE TABLE IF NOT EXISTS "Report" (
	"id"	INTEGER,
	"quarter"	TEXT,
	"year"	TEXT,
	"description"	TEXT,
	"corporation"	INTEGER,
	"report_type"	INTEGER,
	"date"	TEXT,
	FOREIGN KEY("corporation") REFERENCES "Corporation"("id"),
	FOREIGN KEY("report_type") REFERENCES "ReportType"("id"),
	PRIMARY KEY("id")
);
COMMIT;
