# 0003 - Deposit and VAT handling in value fields

Status: accepted (wave 2)

## Context

`omsaetning_dkk` in the extract is gross: it includes 25 per cent VAT and, for
drinks lines, the container deposit. Elasticity work on gross values produced
coefficients that moved with deposit class rather than with price.

## Decision

Strip deposit first using the class rates in `client.deposit_dkk`, then remove
VAT, and use the resulting net value everywhere downstream. Keep the gross
value on the primary table so the totals can still be reconciled against the
client's sales report.

## Consequences

- The deposit rates are a client parameter, not a constant, but the assumption
  that deposit is inside the line value is baked into the pricing helpers.
- Any client without a deposit scheme needs the removal disabled rather than
  set to zero; a zero rate still forces the drinks join.
- Reconciliation to finance is done on gross, accuracy reporting on net. The
  two numbers in the pack are deliberately different.
