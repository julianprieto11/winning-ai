import pandas as pd
import numpy as np

MATCHUP = "datos/contexto_matchup.csv"
EQUIPOS = "datos/contexto_equipos.csv"
REVISION = "datos/revision_matchup_nan.csv"
SALIDA = "datos/diagnostico_causa_matchup_nan.csv"

CONFIG = {
    "ARQ": {"propio":["goalkeeperSaves","ballRecovery","totalClearance"],"rival":["shotsOnGoal","totalShotsOnGoal","expectedGoals","totalShotsInsideBox","touchesInOppBox"],"interaccion":["shotsOnGoal","totalShotsOnGoal","expectedGoals"]},
    "DEF": {"propio":["passes","accuratePasses","ballPossession","ballRecovery","duelWonPercent"],"rival":["expectedGoals","shotsOnGoal","totalShotsOnGoal","totalShotsInsideBox","touchesInOppBox","ballPossession"],"interaccion":["passes","accuratePasses","ballPossession","expectedGoals","shotsOnGoal"]},
    "VOL": {"propio":["passes","accuratePasses","ballPossession","duelWonPercent","ballRecovery","freeKicks"],"rival":["ballPossession","passes","accuratePasses","duelWonPercent","totalClearance"],"interaccion":["passes","accuratePasses","ballPossession","shotsOnGoal"]},
    "DEL": {"propio":["expectedGoals","shotsOnGoal","totalShotsInsideBox","touchesInOppBox","bigChanceCreated","accuratePasses","passes"],"rival":["expectedGoals","expectedGoalsOnTarget","shotsOnGoal","totalShotsInsideBox","touchesInOppBox","bigChanceCreated"],"interaccion":["expectedGoals","expectedGoalsOnTarget","shotsOnGoal"]},
}

def pos(x):
    if pd.isna(x): return None
    x=str(x).upper().strip()
    if x in {"GK","G","ARQ","GOALKEEPER","ARQUERO"}: return "ARQ"
    if x in {"D","DF","DEF","DEFENDER","DEFENSA"}: return "DEF"
    if x in {"M","MF","MID","VOL","MIDFIELDER","VOLANTE"}: return "VOL"
    if x in {"F","FW","FWD","DEL","FORWARD","ATTACKER","DELANTERO"}: return "DEL"
    return None

def mean_valid(g,col):
    if g is None or g.empty or col not in g.columns: return np.nan
    s=pd.to_numeric(g[col],errors="coerce").dropna()
    return s.mean() if not s.empty else np.nan

print("="*70)
print("DIAGNOSTICO CAUSA MATCHUP NaN")
print("="*70)

e=pd.read_csv(EQUIPOS,low_memory=False)
rev=pd.read_csv(REVISION,low_memory=False)
rev=rev[rev["estado"]=="REVISAR_JUGO"].copy()

e["fecha"]=pd.to_datetime(e["pitchapi_fecha"],errors="coerce").dt.normalize()

todas=set()
for c in CONFIG.values():
    todas.update(c["propio"]); todas.update(c["rival"]); todas.update(c["interaccion"])
disp={v for v in todas if f"sofascore_{v}" in e.columns and f"rival_{v}" in e.columns}

cols=["match_id","fecha","team_id","team_name"]
for v in sorted(disp): cols += [f"sofascore_{v}",f"rival_{v}"]
eq=e[cols].groupby(["match_id","team_id"],as_index=False).first()

mapa=e[["match_id","team_id","pitchapi_home_team_id","pitchapi_away_team_id"]].drop_duplicates(["match_id","team_id"]).copy()
mapa["rival_team_id"]=np.where(mapa["team_id"]==mapa["pitchapi_home_team_id"],mapa["pitchapi_away_team_id"],np.where(mapa["team_id"]==mapa["pitchapi_away_team_id"],mapa["pitchapi_home_team_id"],np.nan))
eq=eq.merge(mapa[["match_id","team_id","rival_team_id"]],on=["match_id","team_id"],how="left")

for v in sorted(disp):
    propia=f"sofascore_{v}"; concedida=f"rival_{v}"
    contra=eq[["match_id","team_id",propia,concedida]].copy().rename(columns={"team_id":"_rival_join",propia:"_opp_sofa",concedida:"_opp_rival"})
    eq=eq.merge(contra,left_on=["match_id","rival_team_id"],right_on=["match_id","_rival_join"],how="left")
    eq[propia]=eq[propia].combine_first(eq["_opp_rival"])
    eq[concedida]=eq[concedida].combine_first(eq["_opp_sofa"])
    eq.drop(columns=["_rival_join","_opp_sofa","_opp_rival"],errors="ignore",inplace=True)

hist={tid:g.sort_values("fecha").copy() for tid,g in eq.groupby("team_id")}
out=[]

for _,r in rev.iterrows():
    fecha=pd.to_datetime(r["date"],errors="coerce").normalize()
    posi=pos(r["position"])
    fila=eq[(eq["match_id"]==r["match_id"]) & (eq["team_name"].astype(str)==str(r["team_name"]))]
    if fila.empty:
        out.append({**r.to_dict(),"causa":"NO_SE_ENCONTRO_EQUIPO_PARTIDO"})
        continue
    tid=fila.iloc[0]["team_id"]; rid=fila.iloc[0]["rival_team_id"]
    hp=hist.get(tid,pd.DataFrame()); hr=hist.get(rid,pd.DataFrame())
    hp=hp[hp["fecha"]<fecha]; hr=hr[hr["fecha"]<fecha]
    cfg=CONFIG.get(posi,{"propio":[],"rival":[],"interaccion":[]})
    vp=[v for v in cfg["propio"] if v in disp and not pd.isna(mean_valid(hp,f"sofascore_{v}"))]
    vr=[v for v in cfg["rival"] if v in disp and not pd.isna(mean_valid(hp,f"rival_{v}"))]
    vi=[]
    for v in cfg["interaccion"]:
        if v not in disp: continue
        propio=mean_valid(hp,f"sofascore_{v}")
        if posi=="ARQ": rival=mean_valid(hr,f"sofascore_{v}")
        elif posi=="DEL": rival=mean_valid(hr,f"rival_{v}")
        else: rival=mean_valid(hr,f"sofascore_{v}")
        if not pd.isna(propio) and not pd.isna(rival): vi.append(v)
    if len(hp)==0 or len(hr)==0: causa="SIN_HISTORIAL_PROPIO_O_RIVAL"
    elif not vp and not vr and not vi: causa="NINGUN_COMPONENTE_TIENE_DATOS"
    elif not vp: causa="COMPONENTE_PROPIO_SIN_DATOS"
    elif not vr: causa="COMPONENTE_RIVAL_SIN_DATOS"
    elif not vi: causa="SOLO_FALLA_INTERACCION"
    else: causa="HAY_DATOS_PERO_EL_MATCHUP_NO_SE_GENERO"
    out.append({**r.to_dict(),"team_id_calculado":tid,"rival_id_calculado":rid,"hist_propio_partidos":len(hp),"hist_rival_partidos":len(hr),"n_propio":len(vp),"n_rival":len(vr),"n_interaccion":len(vi),"variables_propio":",".join(vp),"variables_rival":",".join(vr),"variables_interaccion":",".join(vi),"causa":causa})

df=pd.DataFrame(out)
df.to_csv(SALIDA,index=False,encoding="utf-8-sig")
print(f"Casos REVISAR_JUGO analizados: {len(df)}")
print("\nCAUSA:")
print(df["causa"].value_counts().to_string())
print("\nPOR POSICION:")
print(pd.crosstab(df["position"],df["causa"]).to_string())
print(f"\nARCHIVO: {SALIDA}")
print("\nPRIMEROS CASOS:")
print(df[["date","player_name","team_name","rival_team_name","position","hist_propio_partidos","hist_rival_partidos","n_propio","n_rival","n_interaccion","causa"]].head(30).to_string(index=False))
