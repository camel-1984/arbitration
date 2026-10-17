# 16_start_tuning

## Question / hypothesis

Нужны ли модели со стартом более глубокие деревья CatBoost или другой вес CatBoost в ансамбле?

## Motivation

- **Sourcing strategy:** my-pick
- **Source(s):** 14: со стартом в цене больше взаимодействий (перелом старт/рынок), параметры CatBoost подбирались для модели без старта.
- **Why this matters:** проверка, что модель со стартом не недонастроена.

## Method

- **Files touched:** только scratch-скрипт.
- **Change versus baseline (or previous experiment):** CatBoost со стартом: depth 4 / l2 10 (текущий), depth 6 / l2 10, depth 6 / l2 3, depth 8 / l2 10 / lr 0.03; вес CatBoost в ансамбле 0.3 / 0.5 / 0.7; коридор k = 1.30.
- **Cross-validation:** честный CV из 04, признаки 14.
- **Out of scope for this experiment:** —

## Risks / things that could invalidate the result

- Разницы меньше 0.3 п.п. сравнимы с шумом CatBoost.

## Status

- **State:** done
- **Approved by user on:** 2026-10-16 (общее разрешение работать над улучшением модели)
- **Headline result:** линейная со стартом отдельно 23.7% / pinball 0.148, CatBoost отдельно 22.7-23.0% / 0.145-0.147; ансамбль: текущий (d4, вес 0.5) 22.1% / 0.143; лучший по pinball d6 вес 0.5 - 22.2% / 0.142; вес 0.7 - 22.3-22.7%. Глубже деревья сужают коридор (покрытие CatBoost до 36%).
- **Implication for next iteration:** параметры не меняются; алгоритмический резерв модели со стартом исчерпан.
