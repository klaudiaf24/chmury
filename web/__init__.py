from flask import Flask, request, render_template, redirect
from neo4j import GraphDatabase, basic_auth
from flask_bootstrap import Bootstrap


app=Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = '5791628bb0b13ce0c676dfde280ba245'


DATABASE_USERNAME = 'u7fil'
DATABASE_PASSWORD = '297858'
DATABASE_URL      = 'bolt://neo4j.fis.agh.edu.pl:7687'

Bootstrap(app)

driver = GraphDatabase.driver(DATABASE_URL, auth=basic_auth(DATABASE_USERNAME, DATABASE_PASSWORD))

from web import routes
