# Panel Trucking Pardey

Web estática con las cifras de las campañas de email a transportistas de Pardey Insurance.

- `index.html`: la página. Lee `data.json`.
- `data.json`: lo genera `build_data.py` a partir de la respuesta de Brevo
  (`email_campaign_management_get_email_campaigns`, `statistics=globalStats`).
- `static/`: datos fijos (verificación de leads, envío de Momentum del 28-oct, rebotes de octubre)
  y, opcional, `respuestas.json` = `{"<nombre de campaña>": <respuestas>}` para contarlas a mano.

Solo se publican totales y cifras de campañas. Nunca nombres, teléfonos ni correos de leads.
