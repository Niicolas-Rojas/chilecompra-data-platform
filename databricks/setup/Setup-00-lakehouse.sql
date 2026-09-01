-- Databricks notebook source
CREATE CATALOG chilecompra
MANAGED LOCATION 'abfss://lakehouse@stchilecompradev.dfs.core.windows.net/chilecompra';

CREATE SCHEMA chilecompra.bronze;

CREATE SCHEMA chilecompra.silver;

CREATE SCHEMA chilecompra.gold;