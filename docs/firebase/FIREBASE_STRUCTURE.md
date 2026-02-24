# Firebase RTDB Structure

## `/answer_keys/`

```
answer_keys/
└── {teacher_uid}/
    └── {assessment_uid}/
        ├── assessment_uid      : string
        ├── answer_key/
        │   ├── Q1              : string   e.g. "A", "TRUE", "CPU", "essay_answer"
        │   ├── Q2              : string
        │   └── ...Qn
        ├── total_questions     : number
        ├── image_urls/
        │   ├── 0               : string   (Cloudinary URL)
        │   └── ...
        ├── image_public_ids/
        │   ├── 0               : string   (Cloudinary public_id)
        │   └── ...
        ├── created_by          : string   (teacher_uid)
        ├── created_at          : timestamp
        ├── updated_at          : timestamp
        ├── section_uid         : string
        └── subject_uid         : string
```

---

## `/answer_sheets/`

```
answer_sheets/
└── {teacher_uid}/
    └── {assessment_uid}/
        └── {student_id}/
            ├── student_id          : string
            ├── assessment_uid      : string
            ├── answer_sheet/
            │   ├── Q1              : string   e.g. "A", "TRUE", "missing_answer"
            │   ├── Q2              : string
            │   └── ...Qn
            ├── total_score         : number
            ├── total_questions     : number
            ├── is_final_score      : boolean
            ├── breakdown/
            │   └── Q1/
            │       ├── student_answer  : string
            │       ├── correct_answer  : string
            │       └── checking_result : boolean | "pending"
            ├── image_urls/
            │   ├── 0               : string   (Cloudinary URL)
            │   └── ...
            ├── image_public_ids/
            │   ├── 0               : string   (Cloudinary public_id)
            │   └── ...
            ├── checked_by          : string   (teacher_uid)
            ├── checked_at          : timestamp
            ├── updated_at          : timestamp
            ├── section_uid         : string
            └── subject_uid         : string
```

---

## `/users_temp_code/`

```
users_temp_code/
└── {temp_code}/          e.g. "12345678"
    ├── uid               : string   (teacher_uid)
    └── username          : string
```

---

## `/users/`

```
users/
└── teachers/
    └── {teacher_uid}/
        └── ...           (validated by validate_teacher_exists)
```

---

## `/assessments/`

```
assessments/
└── {teacher_uid}/
    └── {assessment_uid}/
        ├── section_uid   : string
        └── subject_uid   : string
```