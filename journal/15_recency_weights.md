# 15_recency_weights

## Question / hypothesis

Помогают ли веса обучающих лотов, убывающие с давностью публикации (полураспад 365 и 180 дней), против дрейфа рынка?

## Motivation

- **Sourcing strategy:** my-pick
- **Source(s):** 10: признак месяца сильный, то есть цены при тех же характеристиках меняются во времени.
- **Why this matters:** свежие сделки лучше отражают текущий рынок.

## Method

- **Files touched:** только scratch-скрипт.
- **Change versus baseline (or previous experiment):** sample_weight = 0.5^(дней до последнего лота train / полураспад) в QuantileRegressor и CatBoost; ансамбль без старта (365, 180) и со стартом (365).
- **Cross-validation:** честный CV из 04.
- **Out of scope for this experiment:** —

## Risks / things that could invalidate the result

- Веса уменьшают эффективный объём train, который и так мал в первых фолдах.

## Status

- **State:** done
- **Approved by user on:** 2026-10-16 (общее разрешение работать над улучшением модели)
- **Headline result:** без старта: 365 дней MdAPE 27.5% / pinball 0.176 (без весов 27.4% / 0.176), 180 дней 28.9% / 0.183; со стартом 365 дней 23.4% / 0.145 (без весов 23.2% / 0.145).
- **Implication for next iteration:** не принимается: признак месяца уже учитывает тренд, веса только уменьшают данные.
