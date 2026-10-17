# 01_baseline

## Question / hypothesis

Какую точность даёт прогноз без обучения: квантили цен похожих лотов, проданных раньше?

## Motivation

- **Sourcing strategy:** user
- **Source(s):** лестница моделей из дизайн-дока (раздел 2.1): медиана похожих лотов → линейная регрессия → CatBoost.
- **Why this matters:** нижняя планка, которую любая модель обязана побить; заодно показывает, где не хватает похожих лотов.

## Method

- **Files touched:** `src/models/baseline.py`, `src/models/evaluate.py`
- **Change versus baseline (or previous experiment):** первый эксперимент. Для лота ищутся похожие в обучающей части по каскаду: марка+модель с годом ±1, ±3, марка+модель, марка с годом ±2, год ±1, все лоты; уровень выбирается, если похожих не меньше 5. Прогноз - P25/P50/P75 их цен.
- **Cross-validation:** временной, expanding window, 4 квартала 2025.
- **Out of scope for this experiment:** флаги, регион, мощность.

## Risks / things that could invalidate the result

- Квантили похожих лотов не учитывают, что похожие лоты не совсем похожи, поэтому коридор занижен по ширине.

## Status

- **State:** done
- **Approved by user on:** 2026-10-16
- **Headline result:** MdAPE 37.1%, промах > 50% 38.7%, покрытие 39.5%, pinball 0.226 (среднее по 4 фолдам)
- **Implication for next iteration:** уровень "марка+модель" без окна по году даёт MdAPE 60% (редкие модели, много поколений) - нужна модель, которая складывает эффект модели и возраста.
