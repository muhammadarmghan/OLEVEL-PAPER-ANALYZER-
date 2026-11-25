"""Reference data and demo accounts. Idempotent: safe to run repeatedly.

The topic tree is a STARTER for Physics (5054). Replace/extend it with the
official Cambridge syllabus before relying on topic statistics.
"""
from .extensions import db
from .models import (
    CommandWord, ExamBoard, ExamSession, PaperComponent, PaperVariant, Qualification,
    QuestionType, Role, Subject, SyllabusVersion, Topic, TopicKeyword, Unit, User,
)

ROLES = ["student", "contributor", "admin"]
QUESTION_TYPES = {"mcq": "Multiple choice", "structured": "Structured", "essay": "Essay", "numerical": "Numerical"}
COMMAND_WORDS = ["state", "describe", "explain", "calculate", "define", "suggest", "compare", "determine", "name", "outline"]
SUBJECTS = {"5054": "Physics", "5070": "Chemistry"}
COMPONENTS = [(1, "Multiple Choice", "mcq", 40), (2, "Theory", "structured", 80)]
YEARS, SERIES = range(2018, 2025), ("s", "w")

PHYSICS_TOPICS = {  # unit number -> (title, [(code, title, keywords)])
    1: ("Motion, forces and energy", [
        ("1.1", "Physical quantities and measurement", ["measurement", "vernier", "micrometer", "calipers", "vector", "scalar", "metre rule"]),
        ("1.2", "Motion", ["speed", "velocity", "acceleration", "distance-time", "speed-time", "gradient"]),
        ("1.3", "Mass and weight", ["mass", "weight", "gravitational field", "density", "kilogram"]),
        ("1.5", "Forces", ["force", "newton", "friction", "resultant", "hooke", "spring", "circular motion", "moment"]),
        ("1.7", "Energy, work and power", ["work", "power", "kinetic", "efficiency", "gravitational", "potential energy", "joule", "watt"]),
        ("1.8", "Pressure", ["pressure", "manometer", "barometer", "pascal", "depth"])]),
    2: ("Thermal physics", [
        ("2.1", "Kinetic particle model of matter", ["particles", "gas pressure", "brownian", "solid", "liquid", "gas", "evaporation"]),
        ("2.2", "Thermal properties and temperature", ["temperature", "thermometer", "thermocouple", "liquid-in-glass", "heat capacity", "specific heat", "thermal expansion", "latent heat", "melting", "boiling"]),
        ("2.3", "Transfer of thermal energy", ["conduction", "convection", "radiation", "thermal energy", "insulation", "emitter", "absorber"])]),
    3: ("Waves", [
        ("3.1", "General properties of waves", ["wave", "wavelength", "frequency", "amplitude", "longitudinal", "transverse", "wavefront"]),
        ("3.2", "Light", ["reflection", "refraction", "lens", "focal length", "refractive index", "critical angle", "total internal reflection", "mirror"]),
        ("3.3", "Electromagnetic spectrum", ["electromagnetic", "spectrum", "infrared", "ultraviolet", "x-ray", "microwave", "gamma ray", "radio"]),
        ("3.4", "Sound", ["sound", "echo", "ultrasound", "pitch", "loudness", "compression", "rarefaction"])]),
    4: ("Electricity and magnetism", [
        ("4.1", "Magnetism", ["magnet", "magnetic field", "north pole", "south pole", "ferrous", "induced magnetism"]),
        ("4.2", "Electrical quantities", ["current", "voltage", "resistance", "charge", "electromotive force", "potential difference", "ohm", "ampere", "coulomb"]),
        ("4.3", "Electric circuits", ["circuit", "series", "parallel", "resistor", "diode", "switch", "ammeter", "voltmeter", "potential divider"]),
        ("4.4", "Practical electricity", ["fuse", "circuit breaker", "earthing", "insulation", "power", "electrical safety"]),
        ("4.5", "Electromagnetic effects", ["transformer", "induction", "motor", "generator", "coil", "solenoid", "dynamo", "relay"])]),
    5: ("Nuclear physics", [
        ("5.1", "The nuclear atom", ["nucleus", "proton", "neutron", "electron", "isotope", "atomic number", "mass number", "nuclide"]),
        ("5.2", "Radioactivity", ["alpha", "beta", "gamma", "half-life", "decay", "radiation", "geiger", "background radiation"])]),
    6: ("Space physics", [
        ("6.1", "Earth and the Solar System", ["orbit", "planet", "moon", "solar system", "sun", "gravitational attraction"]),
        ("6.2", "Stars and the Universe", ["star", "galaxy", "universe", "redshift", "light-year"])]),
}

CHEMISTRY_TOPICS = {
    1: ("Experimental chemistry", [
        ("1.1", "Experimental design and apparatus", ["apparatus", "burette", "pipette", "cylinder"]),
        ("1.2", "Methods of purification and separation", ["chromatography", "distillation", "filtration", "crystallization"])]),
    2: ("The particulate nature of matter", [
        ("2.1", "Kinetic particle theory", ["diffusion", "melting", "boiling", "solid", "liquid", "gas"]),
        ("2.2", "Atomic structure and bonding", ["proton", "neutron", "electron", "isotope", "covalent", "ionic"])]),
    3: ("Stoichiometry and the mole concept", [
        ("3.1", "Formulae, equations and moles", ["mole", "avogadro", "molar mass", "concentration", "stoichiometry"])]),
    4: ("Chemical energetics and electrochemistry", [
        ("4.1", "Energetics of a reaction", ["exothermic", "endothermic", "enthalpy", "activation energy"]),
        ("4.2", "Electrochemistry", ["electrolysis", "cathode", "anode", "electrolyte"])]),
    5: ("Chemical reactions", [
        ("5.1", "Rate of reaction", ["rate", "catalyst", "surface area", "collision"]),
        ("5.2", "Redox reactions", ["oxidation", "reduction", "reducing agent", "oxidising agent"])]),
    6: ("Acids, bases and salts", [
        ("6.1", "Properties of acids and bases", ["acid", "base", "ph", "alkali", "neutralisation", "litmus"]),
        ("6.2", "Preparation of salts", ["salt", "precipitation", "titration", "insoluble"])]),
    7: ("The Periodic Table and Metals", [
        ("7.1", "Periodic trends and groups", ["group", "period", "halogens", "noble gases", "alkali metals"]),
        ("7.2", "Reactivity series and metal extraction", ["reactivity", "displacement", "blast furnace", "iron", "aluminium"])]),
    8: ("Organic chemistry", [
        ("8.1", "Hydrocarbons (Alkanes and Alkenes)", ["alkane", "alkene", "fractional distillation", "cracking", "combustion"]),
        ("8.2", "Alcohols, Carboxylic Acids and Polymers", ["alcohol", "carboxylic", "polymer", "ester", "fermentation"])]),
}


def get_or_create(model, defaults=None, **lookup):
    obj = model.query.filter_by(**lookup).first()
    if obj is None:
        obj = model(**lookup, **(defaults or {}))
        db.session.add(obj)
        db.session.flush()
    return obj


def seed_all():
    roles = {name: get_or_create(Role, name=name) for name in ROLES}
    for code, name in QUESTION_TYPES.items():
        get_or_create(QuestionType, code=code, defaults={"name": name})
    for word in COMMAND_WORDS:
        get_or_create(CommandWord, word=word)

    board = get_or_create(ExamBoard, short_code="CAIE", defaults={"name": "Cambridge Assessment International Education"})
    qual = get_or_create(Qualification, board_id=board.id, name="O Level")
    for year in YEARS:
        for series in SERIES:
            get_or_create(ExamSession, board_id=board.id, year=year, series_code=series)

    for code, name in SUBJECTS.items():
        subject = get_or_create(Subject, qualification_id=qual.id, code=code, defaults={"name": name})
        for number, comp_name, style, marks in COMPONENTS:
            comp = get_or_create(PaperComponent, subject_id=subject.id, paper_number=number,
                                 defaults={"name": comp_name, "question_style": style, "total_marks": marks})
            for variant in (1, 2, 3):
                get_or_create(PaperVariant, component_id=comp.id, variant_number=variant)
        get_or_create(SyllabusVersion, subject_id=subject.id, version_label="starter",
                      defaults={"valid_from_year": 2023, "is_current": True})

    physics = Subject.query.filter_by(code="5054").one()
    version = physics.syllabus_versions[0]
    for number, (title, topics) in PHYSICS_TOPICS.items():
        unit = get_or_create(Unit, syllabus_version_id=version.id, number=number, defaults={"title": title})
        for order, (code, topic_title, keywords) in enumerate(topics):
            topic = get_or_create(Topic, unit_id=unit.id, code=code,
                                  defaults={"title": topic_title, "display_order": order})
            for kw in keywords:
                get_or_create(TopicKeyword, topic_id=topic.id, keyword=kw)

    chemistry = Subject.query.filter_by(code="5070").one()
    chem_version = chemistry.syllabus_versions[0]
    for number, (title, topics) in CHEMISTRY_TOPICS.items():
        unit = get_or_create(Unit, syllabus_version_id=chem_version.id, number=number, defaults={"title": title})
        for order, (code, topic_title, keywords) in enumerate(topics):
            topic = get_or_create(Topic, unit_id=unit.id, code=code,
                                  defaults={"title": topic_title, "display_order": order})
            for kw in keywords:
                get_or_create(TopicKeyword, topic_id=topic.id, keyword=kw)

    for username, role in (("admin", "admin"), ("contributor", "contributor"), ("student", "student")):
        if not User.query.filter_by(username=username).first():
            user = User(username=username, email=f"{username}@example.com")
            user.set_password("Demo#12345")
            user.roles.append(roles[role])
            db.session.add(user)
    db.session.commit()
