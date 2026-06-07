# RunRecover MVP Summary

RunRecover MVP solves one post-run question: what should an everyday runner do in the next 24 hours to recover well?

The product does not replace a running tracker or medical advice. It translates lightweight inputs into a transparent recovery pressure score and practical recovery actions.

## P0 Loop

1. Enter run data: distance, duration, type, and time period.
2. Enter subjective state: RPE, sleep, fatigue, soreness, tomorrow plan, optional heart rate and symptoms.
3. Backend calculates a 0-100 recovery pressure score.
4. Backend returns the main reasons and safety flags.
5. Template recommendation service returns diet, hydration, sleep, relaxation, tomorrow guidance, and a 24-hour timeline.
6. Frontend renders the score, reason list, advice cards, and timeline.

## Trust Rules

- Rules decide the score. The advice layer does not change it.
- RPE is treated as perceived exertion, not as injury or pain diagnosis.
- If heart rate is missing, the result must not mention high heart rate.
- Safety flags use conservative language and direct users to professional help for concerning symptoms.
