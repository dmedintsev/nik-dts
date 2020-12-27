from fastapi import APIRouter
from fastapi.exceptions import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from dependencies import DB_CONNECTION
from internal.models.db_models import APComponent, APPartnumber, APReplacement

router = APIRouter(
    prefix="/article",
    tags=["article"]
)

engine = create_engine(DB_CONNECTION)
Session = sessionmaker(bind=engine)
session = Session()


@router.get("/{article}", tags=["article"])
def get_article(article: str):
    """

    :return: Article, Description
    """
    article = session.query(APPartnumber).filter(APPartnumber.name == article).first()
    components = session.query(APComponent).filter(APComponent.partnumber == article.id).all()
    temp_id = session.query(APReplacement.replacement_id).filter(APReplacement.partnumber_id == article.id).all()
    replacement_id = [i[0] for i in temp_id]
    replacement = session.query(APComponent.mpn).filter(APComponent.id.in_(replacement_id)).all()
    replacement_names = [j[0] for j in replacement]
    return article, components, replacement_names


@router.put("/{article}", tags=["article"])
def update_article(article: str, article_params: dict, mpn_list: list, replacement: list):
    def diff(old, new):
        to_del = []
        to_add = []
        for comp in old:
            if comp not in new:
                to_del.append(comp)
        for cmp in new:
            if cmp not in old:
                to_add.append(cmp)
        return to_add, to_del


    field_list = [
        "id",
        "name",
        "Description",
        "Library_Ref",
        "Footprint_Ref_1",
        "Footprint_Ref_2",
        "Footprint_Ref_3",
        "Footprint_Ref_4",
        "Footprint_Ref_5",
        "notes"
    ]
    for artcl in article_params:
        if artcl not in field_list:
            raise HTTPException(status_code=400, detail="Bad component description")
    article_id = session.query(APPartnumber.id).filter(APPartnumber.name == article_params['name']).first()
    session.query(APPartnumber).filter(APPartnumber.name == article_params['name']).update(article_params)
    draft_id = session.query(APPartnumber.id).filter(APPartnumber.name == "Draft").first()

    components_old = [i[0] for i in session.query(APComponent.mpn).filter(APComponent.partnumber == article_id).all()]
    # update components
    to_add, to_dell = diff(components_old, mpn_list)
    to_d = session.query(APComponent).filter(APComponent.mpn.in_(to_dell)).all()
    for i in to_d:
        i.partnumber = draft_id
    to_a = session.query(APComponent).filter(APComponent.mpn.in_(to_add)).all()
    for i in to_a:
        i.partnumber = article_id
    del to_add
    del to_dell

    # update replacement
    replacement_ids_old = [i[0] for i in session.query(APReplacement.replacement_id).filter(APReplacement.partnumber_id == article_id).all()]
    replacement_ids_new = [i[0] for i in session.query(APComponent.id).filter(APComponent.mpn.in_(replacement)).all()]
    to_add, to_dell = diff(replacement_ids_old, replacement_ids_new)
    session.execute(APReplacement.__table__.delete().where(APReplacement.replacement_id.in_(to_dell)))
    replacement_new_list = []
    for i in to_add:
        tmp = APReplacement(partnumber_id=article_id,
                            replacement_id=i)
        replacement_new_list.append(tmp)
    session.add_all(replacement_new_list)
    session.commit()
    return True
    pass


@router.post("/{article}", tags=["article"])
def post_article(article: str, article_params: dict, mpn_list: list, replacement: list):
    pass

@router.delete("/{article}", tags=["article"])
def delete_article(article: str):
    try:
        draft_id = session.query(APPartnumber.id).filter(APPartnumber.name == "Draft").first()
        article_params = session.query(APPartnumber).filter(APPartnumber.name == article).first()
        components = session.query(APComponent).filter(APComponent.partnumber == article_params.id).all()
        for i in components:
            i.partnumber = draft_id
        session.execute(APReplacement.__table__.delete().where(APReplacement.partnumber_id == article_params.id))
        session.query(APPartnumber).filter(APPartnumber.name == article).delete()
        session.commit()
    except Exception as e:
        print(e)
        return  HTTPException(status_code=400, detail=f"Problem to delete article {article}")
    return True