from datetime import date
from fastapi import APIRouter, Depends, Query
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from db import get_db


router = APIRouter(prefix="/api/planification", tags=["planification"])

@router.get("/count")
def count_taches(db: Session = Depends(get_db)):
    row = db.execute(text("SELECT COUNT(*) AS n FROM planification_taches")).mappings().first()
    return {"count": row["n"] if row else 0}

@router.get("/table")
def get_taches(db: Session = Depends(get_db)):
    rows = db.execute(text("SELECT * FROM planification_taches")).mappings().all()
    return {"data": rows}

@router.get("/pie-by-thera")
def pie_by_thera(db: Session = Depends(get_db)):
    q = text("""
        SELECT statut AS label, COUNT(*) AS value
        FROM planification_taches
        GROUP BY statut
        ORDER BY value DESC
    """)
    rows = db.execute(q).mappings().all()
    return rows

@router.get("/status-by-month")
def status_by_month(db: Session = Depends(get_db)):
    # Colonnes attendues: mois (mm-aa), statut
    sql = text("""
        SELECT
        CONCAT(
            CASE t.m
            WHEN 1  THEN 'janv' WHEN 2 THEN 'fevr' WHEN 3 THEN 'mars'
            WHEN 4  THEN 'avr'  WHEN 5 THEN 'mai'  WHEN 6 THEN 'juin'
            WHEN 7  THEN 'juil' WHEN 8 THEN 'aout' WHEN 9 THEN 'sept'
            WHEN 10 THEN 'oct'  WHEN 11 THEN 'nov' WHEN 12 THEN 'dec'
            END,
            '-',
            LPAD(MOD(t.y, 100), 2, '0')
        ) AS mois,
        t.statut,
        t.n
        FROM (
        SELECT
            YEAR(date_fin)  AS y,
            MONTH(date_fin) AS m,
            statut,
            COUNT(*) AS n
        FROM planification_taches
        WHERE date_fin IS NOT NULL
        GROUP BY YEAR(date_fin), MONTH(date_fin), statut
        ) AS t
        ORDER BY t.y, t.m;
    """)
    rows = db.execute(sql).mappings().all()
    # rows -> [{"mois": "01-26", "statut": "En cours", "n": 12}, ...]
    return {"data": list(rows)}


@router.get("/months")
def months(db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT DISTINCT
            DATE_FORMAT(date_fin, '%Y-%m') AS ym, 
            DATE_FORMAT(date_fin, '%m') AS mm,
            DATE_FORMAT(date_fin, '%y') AS yy
        FROM planification_taches
        WHERE date_fin IS NOT NULL
        ORDER BY ym DESC
    """)).fetchall()

    mois_fr = {
        "01":"janv","02":"févr","03":"mars","04":"avr","05":"mai","06":"juin",
        "07":"juil","08":"août","09":"sept","10":"oct","11":"nov","12":"déc"
    }

    out = []
    for ym, mm, yy in rows:
        label = f"{mois_fr.get(mm, mm)}-{yy}"
        out.append({"value": ym, "label": label})

    return out


@router.get("/histogram-entites")
def histogram_entites(
    year: Optional[int] = Query(None, ge=2000),
    month: Optional[int] = Query(None, ge=1, le=12),
    db: Session = Depends(get_db),
):
    if year is not None and month is not None:
        sql = text("""
            SELECT entites AS entite, COUNT(*) AS nb
            FROM planification_taches
            WHERE date_fin IS NOT NULL
              AND YEAR(date_fin)=:y AND MONTH(date_fin)=:m
            GROUP BY entites
            ORDER BY nb DESC, entite ASC
        """)
        params = {"y": year, "m": month}
    else:
        sql = text("""
            SELECT entites AS entite, COUNT(*) AS nb
            FROM planification_taches
            WHERE date_fin IS NOT NULL
            GROUP BY entites
            ORDER BY nb DESC, entite ASC
        """)
        params = {}

    return db.execute(sql, params).mappings().all()

@router.get("/stack100-entites-statuts")
def stack100_entites_statuts(
    year: Optional[int] = Query(None, ge=2000),
    month: Optional[int] = Query(None, ge=1, le=12),
    db: Session = Depends(get_db),
):
    # ✅ Si filtre mois actif
    if year is not None and month is not None:
        sql = text("""
            SELECT entites AS entite,
                   COALESCE(statut, 'Non défini') AS statut,
                   COUNT(*) AS nb
            FROM planification_taches
            WHERE date_fin IS NOT NULL
              AND YEAR(date_fin)=:y AND MONTH(date_fin)=:m
            GROUP BY entites, COALESCE(statut, 'Non défini')
            ORDER BY entite ASC
        """)
        params = {"y": year, "m": month}
    else:
        # ✅ Tout
        sql = text("""
            SELECT entites AS entite,
                   COALESCE(statut, 'Non défini') AS statut,
                   COUNT(*) AS nb
            FROM planification_taches
            WHERE date_fin IS NOT NULL
            GROUP BY entites, COALESCE(statut, 'Non défini')
            ORDER BY entite ASC
        """)
        params = {}

    return db.execute(sql, params).mappings().all()


@router.get("/gantt")
def gantt(
    start: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="YYYY-MM-DD"),
    entites: str = Query("ALL"),
    statut: str = Query("ALL"),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    filters = []
    params: Dict[str, Any] = {}

    # Filtre responsable (entites)
    if entites != "ALL":
        filters.append("entites = :entites")
        params["entites"] = entites

    # Filtre statut
    if statut != "ALL":
        filters.append("statut = :statut")
        params["statut"] = statut

    # Filtre période basé sur date_fin
    if start:
        filters.append("date_fin >= :start")
        params["start"] = start
    if end:
        filters.append("date_fin <= :end")
        params["end"] = end

    where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""

    sql = text(f"""
        SELECT
            id,
            entites,
            taches,
            DATE_FORMAT(date_debut, '%Y-%m-%d') AS date_debut,
            DATE_FORMAT(date_fin, '%Y-%m-%d') AS date_fin,
            mois,
            statut,
            acteurs,
            dependance,
            observations
        FROM planification_taches
        {where_sql}
        ORDER BY date_debut ASC, date_fin ASC, id ASC
    """)

    rows = db.execute(sql, params).mappings().all()
    return [dict(r) for r in rows]


@router.get("/gantt/filters")
def gantt_filters(db: Session = Depends(get_db)) -> Dict[str, Any]:
    # valeurs distinctes pour alimenter les selects
    entites = db.execute(text("SELECT DISTINCT entites FROM planification_taches ORDER BY entites")).scalars().all()
    statuts = db.execute(text("SELECT DISTINCT statut FROM planification_taches ORDER BY statut")).scalars().all()

    return {
        "entites": [e for e in entites if e],
        "statuts": [s for s in statuts if s],
    }


def _distinct_values(db: Session, column_name: str):
    # ⚠️ column_name doit être une valeur contrôlée (on ne prend pas du user input ici)
    sql = text(f"""
        SELECT DISTINCT {column_name} AS v
        FROM planification_taches
        WHERE {column_name} IS NOT NULL AND TRIM({column_name}) <> ''
        ORDER BY v ASC
    """)
    rows = db.execute(sql).fetchall()
    return [{"value": r.v, "label": r.v} for r in rows]

@router.get("/entites")
def get_entites(db: Session = Depends(get_db)):
    return _distinct_values(db, "entites")

@router.get("/statuts")
def get_statuts(db: Session = Depends(get_db)):
    return _distinct_values(db, "statut")

@router.get("/acteurs")
def get_acteurs(db: Session = Depends(get_db)):
    return _distinct_values(db, "acteurs")

@router.get("/micro")
def get_micro(start: date, end: date, db: Session = Depends(get_db)):
    rows = db.execute(
        text("""
            SELECT id, entites, taches, date_debut, date_fin, mois, statut, acteurs, dependance, observations
            FROM planification_taches
            WHERE date_fin >= :start AND date_debut <= :end
            ORDER BY id ASC
        """),
        {"start": start, "end": end}   # ✅ IMPORTANT
    ).mappings().all()

    return [dict(r) for r in rows]

