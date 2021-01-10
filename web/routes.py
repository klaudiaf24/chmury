import os
import secrets

from flask import Flask
from flask import render_template
from flask import url_for
from flask import flash
from flask import redirect
from flask import Response
from flask import request
from flask_bootstrap import Bootstrap
from flask import jsonify
from web import app
from web import driver

import time, json, re


@app.route("/")
@app.route("/home")
def route_home():
    return render_template('home.html')

@app.route("/show")
def route_show_gen():
    return render_template('show.html')

@app.route("/addH")
def route_add_house_form():
    return render_template('add_house.html')

@app.route("/addP", methods=["GET", "POST"])
def route_add_person_form():
    if request.method == "GET":
        with driver.session() as session:
            women = list_all_women(session)
            men = list_all_men(session)
            houses = list_all_house(session)
            return render_template("add_person.html", men=men, women=women, houses=houses)
    else:
        return render_template("add_person.html")


@app.route("/add")
def route_add_gen():
    return render_template('add.html')

@app.route("/find")
def route_find_gen(): 
    return render_template('find.html')

@app.route("/findperson", methods=["GET", "POST"])
def route_find_person(): 
    if request.method == "POST":
        with driver.session() as session:
            if request.form["submit"] == "find":
                name = request.form['name']
                house = get_house(session, name)
                mother = get_mother(session, name)
                father = get_father(session, name)
                children = get_children(session, name)
                siblings = get_siblings(session, name)

                data = dict()
                data['name'] = name
                data['house'] = house
                data['mother'] = mother
                data['father'] = father
                data['children'] = children
                data['siblings'] = siblings

                if house:
                    dataStr = "name=" + str(data['name']) + "&house=" + str(data['house']) +  "&mother=" + str(data['mother']) +  "&father=" + str(data['father']) +"&children=" + str(data['children']) +"&siblings=" + str(data['siblings'])
                    return redirect(url_for('route_show_person', data=dataStr))
                else:
                    flash('Nie ma takiej osoby w bazie!', 'danger')
                    return redirect(url_for('route_find_person'))
                    
    return render_template('find.html')


@app.route("/show/<data>", methods=['GET','POST'])
def route_show_person(data):
    name = re.search('name=(.[^&]*)&', data).group(1)
    house = re.search('house=(.[^&]*)&', data).group(1)
    mother = re.search('mother=(.[^&]*)&', data).group(1)
    father = re.search('father=(.[^&]*)&', data).group(1)
    children = re.search('children=(.[^&]*)&', data).group(1)
    siblings = re.search('siblings=(.[^&]*)', data).group(1)
    return render_template('show_person.html', name=name, house=house, mother=mother, father=father, children=children, siblings=siblings)


@app.route("/show/house", methods=["GET", "POST"])
def route_show_house(): 
    with driver.session() as session:
        houses=list_all_house(session)
        return render_template('show_house.html', houses=houses)

@app.route("/show/people", methods=["GET", "POST"])
def route_show_all_people(): 
    with driver.session() as session:
        people=list_all_people(session)
        return render_template('show_all_people.html', people=people)

@app.route("/add/house", methods=["GET", "POST"])
def route_add_house():
    if request.method == "POST":
        with driver.session() as session:
            if request.form["submit"] == "add_house":
                name = request.form['name']
                motto = request.form['motto']
                query = "CREATE ("+ name + ":House_GenTree {name:'" + name + "', motto:'" + motto + "'})"
                results = session.run(query)
                flash('Dodano nowy ród!', 'success')
                return redirect(url_for('route_show_house'))
    else:
        return render_template("add_house.html")

@app.route("/add/person", methods=["GET", "POST"])
def route_add_person():
    if request.method == "POST":
        with driver.session() as session:
            if request.form["submit"] == "add_person":
                name = request.form['name']
                mother = request.form['mother']
                father = request.form['father']
                house = request.form['house']
                gender = request.form['gender']

                query = "CREATE ("+ name.replace(" ", "") + ":Person_GenTree {name:'" + name + "', gender:'" + gender + "'})"
                results = session.run(query)
                
                # mother
                if mother != 0:
                    query_mother =  f"MATCH (a:Person_GenTree), (b:Person_GenTree) " + \
                    f"WHERE a.name = '" + name + f"' AND b.name ='" + mother + \
                    f"' CREATE (a)-[r:MOTHER]->(b) RETURN type(r)"
                    results = session.run(query_mother)
                
                # father
                if father != 0:
                    query_father = f"MATCH (a:Person_GenTree), (b:Person_GenTree) " + \
                    f"WHERE a.name = '" + name + f"' AND b.name ='" + father + \
                    f"' CREATE (a)-[r:FATHER]->(b) RETURN type(r)"
                    results = session.run(query_father)
                
                # house
                query_house =f"MATCH (a:Person_GenTree), (b:House_GenTree) " + \
                f"WHERE a.name = '" + name + f"' AND b.name ='" + house + \
                f"' CREATE (a)-[r:BELONG]->(b) RETURN type(r)"
                results = session.run(query_house)
                
                flash('Dodano nowego członka rodu ' + house, 'success')
                return redirect(url_for('route_show_all_people'))
    else:
        return redirect(url_for('route_add_person_form'))


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    return app.send_static_file("index.html")

#######################################################

def normalize_query_param(value):
    return value if len(value) > 1 else value[0]


def normalize_query(params):
    params_non_flat = params.to_dict(flat=False)
    return {k: normalize_query_param(v) for k, v in params_non_flat.items()}


def get_house(session, name):
    query = """MATCH (p:Person_GenTree), (h:House_GenTree) 
    WHERE p.name = \"""" + name + """\" and
    (p) - [:BELONG] -> (h) 
    RETURN h.name as name"""
    results = session.run(query)
    l = []
    for res in results:
        l.append(res['name'])
    return l

def get_mother(session, name):
    query = """MATCH (p:Person_GenTree), (pm:Person_GenTree) 
    WHERE p.name = \"""" + name + """\" and
    (p) - [:MOTHER] -> (pm) 
    RETURN pm.name as name"""
    results = session.run(query)
    l = []
    for res in results:
        l.append(res['name']) 
    if not l:
        l.append("brak danych")
    return l[0]

def get_children(session, name):
    query = """MATCH (p:Person_GenTree), (pm:Person_GenTree) 
    WHERE 
    pm.name = \"""" + name + """\" AND (p) - [:MOTHER] -> (pm) 
    OR
    pm.name = \"""" + name + """\" AND (p) - [:FATHER] -> (pm) 
    RETURN p.name as name"""
    results = session.run(query)
    l = []
    for res in results:
        l.append(res['name']) 
    if not l:
        l.append("brak danych")
    return l

def get_siblings(session, name):
    query = """MATCH (p:Person_GenTree), (pm:Person_GenTree), (sib:Person_GenTree)
    WHERE 
    (p.name = \"""" + name + """\" AND (p) - [:MOTHER] -> (pm) AND (sib) - [:MOTHER] -> (pm) 
    OR
    p.name = \"""" + name + """\" AND (p) - [:FATHER] -> (pm) AND (sib) - [:FATHER] -> (pm))
    AND
    sib.name <> p.name 
    RETURN DISTINCT sib.name as name"""
    results = session.run(query)
    l = []
    for res in results:
        l.append(res['name']) 
    if not l:
        l.append("brak danych")
    return l

def get_father(session, name):
    query = """MATCH (p:Person_GenTree), (pf:Person_GenTree) 
    WHERE p.name = \"""" + name + """\" and
    (p) - [:FATHER] -> (pf) 
    RETURN pf.name as name"""
    results = session.run(query)
    l = []
    for res in results:
        l.append(res['name']) 
    if not l:
        l.append("brak danych")
    return l[0]

def list_all_house(session):
    query = "MATCH (h:House_GenTree) RETURN h.name as name, h.motto as motto ORDER BY h.name"
    results = session.run(query)
    return results

def list_all_people(session):
    query = """MATCH (p:Person_GenTree), (h:House_GenTree) 
    WHERE (p) - [:BELONG] -> (h)
    RETURN p.name as name, h.name as house ORDER BY h.name"""
    results = session.run(query)
    return results

def list_all_women(session):
    query = "MATCH (p:Person_GenTree) WHERE p.gender='k' RETURN p.name as name ORDER BY p.name"
    results = session.run(query)
    return results

def list_all_men(session):
    query = "MATCH (p:Person_GenTree) WHERE p.gender='m' RETURN p.name as name ORDER BY p.name"
    results = session.run(query)
    return results
