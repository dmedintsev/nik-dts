from typing import Text

from sqlalchemy import Column, INTEGER, TEXT, VARCHAR, BOOLEAN, ForeignKey, DATE
from sqlalchemy.dialects.postgresql import TIMESTAMP, JSONB
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class PALog(Base):
    __tablename__ = 'log'
    id = Column('id', INTEGER(), primary_key=True, nullable=False)
    message = Column('message', TEXT())
    timestamp = Column('timestamp', TIMESTAMP(timezone=True), nullable=False)
    action_source = Column('action_source', VARCHAR(length=30))
    actual = Column('actual', BOOLEAN())
    action_type = Column('action_type', VARCHAR(length=30))


class PAManufacturers(Base):
    __tablename__ = 'manufacturer'
    id = Column('id', INTEGER(), primary_key=True, nullable=False)
    manufacturer = Column('manufacturer', VARCHAR(length=255))
    shortname = Column('shortname', VARCHAR(length=20))


class APParamlist(Base):
    __tablename__ = 'param_list'
    id = Column('id', INTEGER(), primary_key=True, nullable=False)
    category = Column('category', VARCHAR(length=255))
    family = Column('family', VARCHAR(length=255))
    param_name = Column('param_name', VARCHAR(length=100))
    index = Column('index', INTEGER(), nullable=False)


class APPartnumber(Base):
    __tablename__ = 'partnumber'
    id = Column('id', INTEGER(), primary_key=True, nullable=False)
    name = Column('name', VARCHAR(length=50))
    Description = Column('Description', VARCHAR(length=255))
    Library_Ref = Column('Library Ref', VARCHAR(length=50))
    Footprint_Ref_1 = Column('Footprint Ref 1', VARCHAR(length=30))
    Footprint_Ref_2 = Column('Footprint Ref 2', VARCHAR(length=30))
    Footprint_Ref_3 = Column('Footprint Ref 3', VARCHAR(length=30))
    Footprint_Ref_4 = Column('Footprint Ref 4', VARCHAR(length=30))
    Footprint_Ref_5 = Column('Footprint Ref 5', VARCHAR(length=30))
    notes = Column('notes', VARCHAR(length=255))


class APReplacement(Base):
    __tablename__ = 'replacement'
    id = Column('id', INTEGER(), primary_key=True, nullable=False)
    partnumber_id = Column('partnumber_id', INTEGER())
    replacement_id = Column('replacement_id', INTEGER(), nullable=False)


class APCategory(Base):
    __tablename__ = 'category'
    id = Column('id', INTEGER(), primary_key=True, nullable=False)
    name = Column('name', VARCHAR(length=50))
    mdbtblname = Column('mdbtblname', VARCHAR(length=100))
    libraryreffile = Column('libraryreffile', VARCHAR(length=255))
    footprintreffile = Column('footprintreffile', VARCHAR(length=255))
    family_list = Column('family_list', JSONB(astext_type=Text()))


class APComponent(Base):
    __tablename__ = 'component'
    id = Column('id', INTEGER(), primary_key=True, nullable=False, )
    mpn = Column('mpn', VARCHAR(length=255))
    category_id = Column('category_id', INTEGER(), ForeignKey('category.id'))
    priority = Column('priority', INTEGER())
    price = Column('price', INTEGER())
    params = Column('params', JSONB(astext_type=Text()))
    provider = Column('provider', VARCHAR(length=30))
    delivery_time = Column('delivery_time', DATE())
    factory = Column('factory', VARCHAR(length=30))
    partnumber = Column('partnumber', INTEGER(), ForeignKey('partnumber.id'))
    validation = Column('validation', BOOLEAN())
