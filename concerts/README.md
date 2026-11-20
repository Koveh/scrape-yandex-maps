# Concerts collectors

Writes into Postgres `koveh.public.concerts`. Airflow DAG: `tst_concerts_collectors_etl`.

| Task | Script | City | Status on insert |
|---|---|---|---|
| `scrape_concerts` | `scrape_concerts.py` | Москва | `pending` (Telegram) |
| `curate_moscow` | `curate_local.py` | Москва | promotes pending → kept/rejected/duplicate |
| `scrape_standupstore` | `scrape_standupstore.py` | Москва | `kept` |
| `scrape_mbronnaya` | `scrape_mbronnaya.py` | Москва | `kept` |
| `scrape_mossovet` | `scrape_mossovet.py` | Москва | `kept` |
| `scrape_mdm` | `scrape_mdm.py` | Москва | `kept` |
| `scrape_afisha_moscow` | `scrape_afisha_moscow.py` | Москва | `kept` (Afisha concerts + theatre) |
| `scrape_yandex_afisha` | `scrape_yandex_afisha_moscow.py` | Москва | `kept` |
| `scrape_moscow_locations` | `scrape_moscow_locations.py` | Москва | `kept` (Lenkom, Satire, MXAT, Helikon, Zaryadye) |
| `scrape_comedypub` | `scrape_comedypub.py` | Вена | `kept` |
| `scrape_flex` | `scrape_flex.py` | Вена | `kept` |
| `scrape_porgy` | `scrape_porgy.py` | Вена | `kept` |
| `scrape_grelleforelle` | `scrape_grelleforelle.py` | Вена | `kept` |
| `scrape_b72` | `scrape_b72.py` | Вена | `kept` |
| `scrape_niedermair` | `scrape_niedermair.py` | Вена | `kept` |
| `scrape_simpl` | `scrape_simpl.py` | Вена | `kept` |
| `scrape_orpheum` | `scrape_orpheum.py` | Вена | `kept` |
| `scrape_reigen` | `scrape_reigen.py` | Вена | `kept` |
| `scrape_casanova` | `scrape_casanova.py` | Вена | `kept` |
| `scrape_globe` | `scrape_globe.py` | Вена | `kept` |
| `scrape_theaterimpark` | `scrape_theaterimpark.py` | Вена | `kept` |
| `scrape_sargfabrik` | `scrape_sargfabrik.py` | Вена | `kept` |
| `scrape_volkstheater` | `scrape_volkstheater.py` | Вена | `kept` |
| `scrape_radiokulturhaus` | `scrape_radiokulturhaus.py` | Вена | `kept` |
| `scrape_metropol` | `scrape_metropol.py` | Вена | `kept` |
| `scrape_theaterwien` | `scrape_theaterwien.py` | Вена | `kept` |
| `scrape_rabenhof` | `scrape_rabenhof.py` | Вена | `kept` |
| `scrape_luckypunch` | `scrape_luckypunch.py` | Вена | `kept` |
| `scrape_marxhalle` | `scrape_marxhalle.py` | Вена | `kept` |
| `scrape_drachengasse` | `scrape_drachengasse.py` | Вена | `kept` |
| `scrape_volksoper` | `scrape_volksoper.py` | Вена | `kept` |
| `scrape_burgtheater` | `scrape_burgtheater.py` | Вена | `kept` |
| `scrape_staatsoper` | `scrape_staatsoper.py` | Вена | `kept` |
| `scrape_muth` | `scrape_muth.py` | Вена | `kept` |
| `scrape_kosmos` | `scrape_kosmos.py` | Вена | `kept` |
| `scrape_palace` | `scrape_palace.py` | Вена | `kept` |
| `scrape_englishtheatre` | `scrape_englishtheatre.py` | Вена | `kept` |
| `scrape_musicalvienna` | `scrape_musicalvienna.py` | Вена | `kept` |
| `scrape_nest` | `scrape_nest.py` | Вена | `kept` |
| `scrape_jazzland` | `scrape_jazzland.py` | Вена | `kept` |
| `scrape_daswerk` | `scrape_daswerk.py` | Вена | `kept` (industrial) |
| `scrape_kunsthalle` | `scrape_kunsthalle.py` | Вена | `kept` (art) |
| `scrape_mqw` | `scrape_mqw.py` | Вена | `kept` (MQ events) |
| `scrape_grafenegg` | `scrape_grafenegg.py` | Нижняя Австрия | `kept` |
| `scrape_festspielhaus` | `scrape_festspielhaus.py` | Нижняя Австрия | `kept` |
| `scrape_landestheater` | `scrape_landestheater.py` | Нижняя Австрия | `kept` |
| `scrape_tonkuenstler` | `scrape_tonkuenstler.py` | Нижняя Австрия | `kept` |
| `scrape_arena` | `scrape_arena.py` | Вена | `kept` |
| `scrape_chelsea` | `scrape_chelsea.py` | Вена | `kept` |
| `scrape_wuk` | `scrape_wuk.py` | Вена | `kept` |
| `scrape_viper` | `scrape_viper.py` | Вена | `kept` |
| `scrape_flucc` | `scrape_flucc.py` | Вена | `kept` |
| `scrape_planet` | `scrape_planet.py` | Вена | `kept` |
| `scrape_stadthalle` | `scrape_stadthalle.py` | Вена | `kept` |
| `scrape_sass` | `scrape_sass.py` | Вена | `kept` |
| `scrape_simpl` | `scrape_simpl.py` | Вена | `kept` |
| `scrape_vindobona` | `scrape_vindobona.py` | Вена | `kept` |
| `scrape_reigen` | `scrape_reigen.py` | Вена | `kept` |
| `scrape_niedermair` | `scrape_niedermair.py` | Вена | `kept` |
| `scrape_stadtsaal` | `scrape_stadtsaal.py` | Вена | `kept` |
| `scrape_orpheum` | `scrape_orpheum.py` | Вена | `kept` |
| `scrape_escape` | `scrape_escape.py` | Вена | `kept` |
| `scrape_konzerthaus` | `scrape_konzerthaus.py` | Вена | `kept` |
| `scrape_metropol` | `scrape_metropol.py` | Вена | `kept` |
| `scrape_dschungel` | `scrape_dschungel.py` | Вена | `kept` |
| `scrape_rausgegangen` | `scrape_rausgegangen.py` | Вена | `kept` |
| `scrape_arena` | `scrape_arena.py` | Вена | `kept` |
| `scrape_chelsea` | `scrape_chelsea.py` | Вена | `kept` |
| `scrape_wuk` | `scrape_wuk.py` | Вена | `kept` |
| `scrape_viper` | `scrape_viper.py` | Вена | `kept` |
| `scrape_flucc` | `scrape_flucc.py` | Вена | `kept` |
| `scrape_planet` | `scrape_planet.py` | Вена | `kept` (Gasometer / Szene / SimmCity) |
| `scrape_stadthalle` | `scrape_stadthalle.py` | Вена | `kept` |
| `scrape_sass` | `scrape_sass.py` | Вена | `kept` |
| `scrape_strom` | `scrape_strom.py` | Мюнхен | `kept` |
| `scrape_muffatwerk` | `scrape_muffatwerk.py` | Мюнхен | `kept` |
| `scrape_feierwerk` | `scrape_feierwerk.py` | Мюнхен | `kept` |
| `scrape_gasteig` | `scrape_gasteig.py` | Мюнхен | `kept` |
| `scrape_rotesonne` | `scrape_rotesonne.py` | Мюнхен | `kept` |
| `scrape_unterfahrt` | `scrape_unterfahrt.py` | Мюнхен | `kept` |
| `scrape_bahnwaerter` | `scrape_bahnwaerter.py` | Мюнхен | `kept` |
| `scrape_vereinsheim` | `scrape_vereinsheim.py` | Мюнхен | `kept` |
| `scrape_lachundschiess` | `scrape_lachundschiess.py` | Мюнхен | `kept` |
| `scrape_lustspielhaus` | `scrape_lustspielhaus.py` | Мюнхен | `kept` |
| `scrape_jungle` | `scrape_jungle.py` | Мюнхен | `kept` |
| `scrape_importexport` | `scrape_importexport.py` | Мюнхен | `kept` |
| `scrape_backstage` | `scrape_backstage.py` | Мюнхен | `kept` |
| `scrape_olympiapark` | `scrape_olympiapark.py` | Мюнхен | `kept` |
| `scrape_grafenegg` | `scrape_grafenegg.py` | Нижняя Австрия | `kept` |
| `scrape_festspielhaus` | `scrape_festspielhaus.py` | Нижняя Австрия | `kept` |
| `scrape_tonkuenstler` | `scrape_tonkuenstler.py` | Нижняя Австрия | `kept` |
| `scrape_landestheater` | `scrape_landestheater.py` | Нижняя Австрия | `kept` |
| `scrape_buehnebaden` | `scrape_buehnebaden.py` | Нижняя Австрия | `kept` |
| `scrape_kunsthalle` | `scrape_kunsthalle.py` | Вена | `kept` |
| `scrape_mqw` | `scrape_mqw.py` | Вена | `kept` |
| `scrape_daswerk` | `scrape_daswerk.py` | Вена | `kept` |
| `scrape_leisure_locations` | `scrape_leisure_locations.py` | Вена | `kept` (Palais Auersperg, Albertina, Secession, Leopold, Club U) |
| `scrape_schallaburg` | `scrape_schallaburg.py` | Нижняя Австрия | `kept` |
| `scrape_mak` | `scrape_mak.py` | Вена | `kept` (art) |
| `scrape_belvedere` | `scrape_belvedere.py` | Вена | `kept` (art) |
| `scrape_praterdome` | `scrape_praterdome.py` | Вена | `kept` (club) |
| `scrape_u4` | `scrape_u4.py` | Вена | `kept` (club) |
| `scrape_szene` | `scrape_szene.py` | Вена | `kept` |
| `scrape_wienersymphoniker` | `scrape_wienersymphoniker.py` | Вена | `kept` |
| `scrape_musikverein` | `scrape_musikverein.py` | Вена | `kept` |
| `scrape_rso` | `scrape_rso.py` | Вена | `kept` (Vienna halls) |
| `scrape_schauspielhaus` | `scrape_schauspielhaus.py` | Вена | `kept` |
| `scrape_p1` | `scrape_p1.py` | Мюнхен | `kept` |
| `scrape_neuraum` | `scrape_neuraum.py` | Мюнхен | `kept` |
| `scrape_freiheitshalle` | `scrape_freiheitshalle.py` | Мюнхен | `kept` |
| `scrape_milla` | `scrape_milla.py` | Мюнхен | `kept` (KULTURpur; official CF) |
| `scrape_rausgegangen_munich` | `scrape_rausgegangen_munich.py` | Мюнхен | `kept` (city feed) |
| `scrape_munich_locations` | `scrape_munich_locations.py` | Мюнхен | `kept` (Zenith, Krone, Substanz, Kammerspiele, Residenz, Olympiahalle, Isarphilharmonie, Herkulessaal, Milla, Prinzregenten, Gärtnerplatz, 089, Harry Klein, Blitz, Cord, Drella, Neuraum, BMW Welt, Tollwood) |
| `scrape_circuskron` | `scrape_circuskron.py` | Мюнхен | `kept` |
| `scrape_substanz` | `scrape_substanz.py` | Мюнхен | `kept` |
| `scrape_kammerspiele` | `scrape_kammerspiele.py` | Мюнхен | `kept` |
| `scrape_residenztheater` | `scrape_residenztheater.py` | Мюнхен | `kept` |
| `scrape_volkstheater_muc` | `scrape_volkstheater_muc.py` | Мюнхен | `kept` |

Comedy Pub task id stays `scrape_comedypub`. Shared helpers: `vienna_common.py`, `munich_common.py`, `yeah_calendar.py`.

Rows get reusable `tags text[]`: picker kinds `concert` / `standup` / `event`, plus extras (`jazz`, `theater`, `comedy`, …). `/concerts` title underlines the kind like the city. Multi-select is `?kind=concert,standup`. `Events` = whole listing. Classifier: `concert_tags.py`.

`/events` extra: `tst_germany_events_collectors_etl` also runs Bayern Innovativ, TUM calendar, appliedAI.

## Add a Vienna / Munich source

1. Copy a `scrape_*.py` next to the others and keep the `ViennaShow` / `ViennaStore` upsert.
2. Set city via `vienna_common.CITY` (`Вена`), `NOE_CITY` (`Нижняя Австрия`), or `MUNICH_CITY` / `MunichStore`.
3. Use a new `SOURCE_CHANNEL` and a stable `source_message_id`.
4. Add `(source, script, task_id)` to `VENUE_SOURCES` in `tst_concerts_collectors_etl.py`.
5. Add the city slug in koveh.com `src/lib/concerts-cities.ts` only if it is a new city.

Dry run:

```bash
python3 /root/automation/concerts/scrape_comedypub.py --dry
python3 /root/automation/concerts/scrape_arena.py --dry
python3 /root/automation/concerts/scrape_muffatwerk.py --dry
```
