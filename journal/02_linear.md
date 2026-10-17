# 02_linear

## Question / hypothesis

Насколько линейная квантильная регрессия на log цены с признаками машины и флагами лучше похожих лотов?

## Motivation

- **Sourcing strategy:** user
- **Source(s):** лестница моделей из дизайн-дока; вывод 01_baseline о редких моделях.
- **Why this matters:** интерпретируемая модель, эффекты флагов при прочих равных.

## Method

- **Files touched:** `src/models/linear.py`
- **Change versus baseline (or previous experiment):** QuantileRegressor (pinball loss, L1) отдельно на P25/P50/P75. Признаки: марка, марка+модель (one-hot, редкие в infrequent), регион, тип должника, возраст через сплайн, log мощности и объёма с индикатором пропуска, месяц публикации, 6 флагов. Этап продажи не используется (известен после торгов). Прогнозы сортируются против пересечения квантилей. alpha и min_frequency подобраны сеткой по среднему pinball на CV.
- **Cross-validation:** тот же временной CV, что у 01_baseline.
- **Out of scope for this experiment:** взаимодействия признаков.

## Risks / things that could invalidate the result

- Гиперпараметры выбраны на тех же фолдах, на которых отчитываемся: цифры CV немного оптимистичны; честная оценка - тест 2026.

## Status

- **State:** done
- **Approved by user on:** 2026-10-16
- **Headline result:** MdAPE 28.3%, промах > 50% 26.7%, покрытие 46.6%, pinball 0.185 (alpha 1e-4, min_frequency 3)
- **Implication for next iteration:** большой выигрыш у бейзлайна; эффекты флагов: не на ходу -26%, кузов -10%, залог +4%. Следующий шаг - нелинейности и взаимодействия (CatBoost).
