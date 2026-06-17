# Filter Evaluation

## מטרת הבדיקה

הבדיקה הנוכחית בודקת רק את המסנן הראשון:

```text
האם הודעה צריכה לעבור לשלב הבא או לא?
```

היא לא בודקת אבחון, CBT, baseline, או התראות להורה.

## הדאטה סט

קובץ:

- [data/filter_eval_cases.jsonl](../data/filter_eval_cases.jsonl)

יש בו 50 הודעות בעברית:

- הודעות רגילות שילדים יכולים לשאול AI.
- הודעות שמדברות על מצב רגשי וצריכות לעבור לשלב הבא.

כל שורה נראית כך:

```json
{"id":"he-011","text":"אני ממש לחוץ מהמבחן מחר ולא מצליח להירדם","expected":{"is_emotionally_relevant":true,"categories":["anxiety","distress"],"risk_hint":"none"}}
```

כרגע לצורך המסנן הראשון, השדה החשוב הוא:

```json
expected.is_emotionally_relevant
```

אם הוא `true`, ההודעה אמורה לעבור לשלב הבא.

## איך מריצים

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_filter_dataset.py
```

## פלט הבדיקה

דוגמה:

```json
{
  "total": 50,
  "should_pass_count": 32,
  "passed_count": 32,
  "correctly_passed_count": 32,
  "missed_count": 0,
  "wrongly_passed_count": 0,
  "passed_cases": [],
  "missed_cases": [],
  "wrongly_passed_cases": []
}
```

## פירוש השדות

### `total`

כמה הודעות יש בדאטה סט.

### `should_pass_count`

כמה הודעות לפי ה-expected אמורות לעבור לשלב הבא.

### `passed_count`

כמה הודעות המודל החליט להעביר לשלב הבא.

### `correctly_passed_count`

כמה הודעות שעברו באמת היו אמורות לעבור.

### `missed_count`

כמה הודעות רגשיות פוספסו.

אלה הודעות שהיו אמורות לעבור אבל המודל סימן כלא רלוונטיות.

### `wrongly_passed_count`

כמה הודעות רגילות עברו בטעות.

אלה הודעות שלא היו אמורות לעבור אבל המודל סימן כרלוונטיות.

### `passed_cases`

כל ההודעות שהמסנן היה מעביר לשלב הבא.

כל פריט כולל:

```json
{
  "id": "he-011",
  "text": "אני ממש לחוץ מהמבחן מחר ולא מצליח להירדם",
  "should_pass": true,
  "passed": true,
  "confidence": 0.85,
  "provider": "openai"
}
```

### `missed_cases`

הודעות שהיו אמורות לעבור אבל לא עברו.

בשלב הזה זה המדד הכי חשוב להקטין.

### `wrongly_passed_cases`

הודעות רגילות שעברו בטעות.

זה פחות מסוכן מפספוס הודעה רגשית, אבל עדיין חשוב כדי לא להציף את השלב הבא.

## הערה חשובה

המסנן הראשון לא אמור להיות המנתח הפסיכולוגי.

אם הודעה עברה לשלב הבא, זה מספיק טוב כרגע. קטגוריות כמו `anxiety`, `distress`, `loneliness` הן עזר, אבל לא המדד המרכזי בשלב הזה.

