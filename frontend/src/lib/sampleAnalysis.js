// Real /v2/analyze payloads captured from the backend against corpus
// resumes -- used by tests and the ?mock= dev harness. Not shipped in any
// user code path.
export const SAMPLE_ANALYSIS = {
  "quality": {
    "mode": "quality",
    "score": 85,
    "available_points": 85,
    "raw_score": 72.4,
    "dimensions": [
      {
        "dimension": "structure",
        "score": 15,
        "max_points": 15,
        "status": "scored",
        "detail": {
          "sections": {
            "experience": true,
            "education": true,
            "skills": true,
            "projects": true,
            "certifications": true
          }
        }
      },
      {
        "dimension": "writing",
        "score": 12.8,
        "max_points": 15,
        "status": "scored",
        "detail": {
          "repeated_words": [
            "gemini"
          ],
          "passive_line_rate": 0,
          "filler_line_rate": 0
        }
      },
      {
        "dimension": "achievements",
        "score": 13.6,
        "max_points": 20,
        "status": "scored",
        "detail": {
          "total_bullets": 14,
          "quantified": 9,
          "qualitative": 1
        }
      },
      {
        "dimension": "skills",
        "score": 15,
        "max_points": 15,
        "status": "scored",
        "detail": {
          "mode": "count",
          "skills_found": 37
        }
      },
      {
        "dimension": "experience",
        "score": 16,
        "max_points": 20,
        "status": "scored",
        "detail": {
          "entries": 2,
          "completeness_pct": 0.75,
          "order_ok": true,
          "order_comparable_pairs": 1,
          "order_violations": 0
        }
      },
      {
        "dimension": "relevance",
        "score": null,
        "max_points": 15,
        "status": "not_applicable"
      }
    ],
    "parse": {
      "status": "ok",
      "columns": [
        1
      ],
      "unclickable_urls": [],
      "invisible_annotation_count": 0
    },
    "contact_links": {
      "summary": "Contact & Links: 0 issues found",
      "issue_count": 0,
      "phones": [
        {
          "raw": "+91 9125812318",
          "is_valid": true,
          "e164": "+919125812318",
          "issue": null
        }
      ],
      "emails": [
        {
          "raw": "anumishra555555@gmail.com",
          "is_valid_syntax": true,
          "is_deliverable": null,
          "issue": null
        }
      ],
      "links": [
        {
          "url": "https://mac-os-portfolio-topaz-one.vercel.app/",
          "status": "ok",
          "http_status": null,
          "platform_issue": null
        },
        {
          "url": "https://linkedin.com/in/anumish",
          "status": "ok",
          "http_status": null,
          "platform_issue": null
        },
        {
          "url": "https://github.com/Anumishra02",
          "status": "ok",
          "http_status": null,
          "platform_issue": null
        },
        {
          "url": "https://at-sync-zeta.vercel.app/",
          "status": "ok",
          "http_status": null,
          "platform_issue": null
        },
        {
          "url": "https://github.com/Anumishra02/ATSync",
          "status": "ok",
          "http_status": null,
          "platform_issue": null
        },
        {
          "url": "https://carval-1.onrender.com/",
          "status": "ok",
          "http_status": null,
          "platform_issue": null
        },
        {
          "url": "https://github.com/Anumishra02/CarVal",
          "status": "ok",
          "http_status": null,
          "platform_issue": null
        },
        {
          "url": "https://github.com/Anumishra02/CodeSense-AI",
          "status": "ok",
          "http_status": null,
          "platform_issue": null
        }
      ],
      "missing": []
    }
  },
  "uncomputable": {
    "mode": "quality",
    "score": 66,
    "available_points": 65,
    "raw_score": 43,
    "dimensions": [
      {
        "dimension": "structure",
        "score": 12,
        "max_points": 15,
        "status": "scored",
        "detail": {
          "sections": {
            "experience": true,
            "education": true,
            "skills": true,
            "projects": false,
            "certifications": true
          }
        }
      },
      {
        "dimension": "writing",
        "score": 15,
        "max_points": 15,
        "status": "scored",
        "detail": {
          "repeated_words": [],
          "passive_line_rate": 0,
          "filler_line_rate": 0
        }
      },
      {
        "dimension": "achievements",
        "score": null,
        "max_points": 20,
        "status": "uncomputable",
        "detail": {
          "reason": "No bulleted achievements found -- quantification can't be assessed"
        }
      },
      {
        "dimension": "skills",
        "score": 0,
        "max_points": 15,
        "status": "scored",
        "detail": {
          "mode": "count",
          "skills_found": 0
        }
      },
      {
        "dimension": "experience",
        "score": 16,
        "max_points": 20,
        "status": "scored",
        "detail": {
          "entries": 2,
          "completeness_pct": 0.75,
          "order_ok": true,
          "order_comparable_pairs": 0,
          "order_violations": 0
        }
      },
      {
        "dimension": "relevance",
        "score": null,
        "max_points": 15,
        "status": "not_applicable"
      }
    ],
    "parse": {
      "status": "ok",
      "columns": [
        1
      ],
      "unclickable_urls": [
        "grace.fernandes.rn@gmail.com"
      ],
      "invisible_annotation_count": 0
    },
    "contact_links": {
      "summary": "Contact & Links: 0 issues found",
      "issue_count": 0,
      "phones": [
        {
          "raw": "+91 98862 05437",
          "is_valid": true,
          "e164": "+919886205437",
          "issue": null
        }
      ],
      "emails": [
        {
          "raw": "grace.fernandes.rn@gmail.com",
          "is_valid_syntax": true,
          "is_deliverable": null,
          "issue": null
        }
      ],
      "links": [
        {
          "url": "https://linkedin.com/in/gracefernandesrn",
          "status": "ok",
          "http_status": null,
          "platform_issue": null
        }
      ],
      "missing": []
    }
  },
  "match": {
    "mode": "match",
    "score": 70,
    "available_points": 100,
    "raw_score": 69.6,
    "dimensions": [
      {
        "dimension": "structure",
        "score": 12,
        "max_points": 15,
        "status": "scored",
        "detail": {
          "sections": {
            "experience": true,
            "education": true,
            "skills": true,
            "projects": true,
            "certifications": false
          }
        }
      },
      {
        "dimension": "writing",
        "score": 10.5,
        "max_points": 15,
        "status": "scored",
        "detail": {
          "repeated_words": [
            "authentication",
            "enhancing"
          ],
          "passive_line_rate": 0,
          "filler_line_rate": 0
        }
      },
      {
        "dimension": "achievements",
        "score": 12,
        "max_points": 20,
        "status": "scored",
        "detail": {
          "total_bullets": 15,
          "quantified": 8,
          "qualitative": 2
        }
      },
      {
        "dimension": "skills",
        "score": 9.5,
        "max_points": 15,
        "status": "scored",
        "detail": {
          "mode": "jd_match",
          "matched": 7,
          "jd_skills": 11
        }
      },
      {
        "dimension": "experience",
        "score": 16,
        "max_points": 20,
        "status": "scored",
        "detail": {
          "entries": 2,
          "completeness_pct": 0.75,
          "order_ok": true,
          "order_comparable_pairs": 1,
          "order_violations": 0
        }
      },
      {
        "dimension": "relevance",
        "score": 9.6,
        "max_points": 15,
        "status": "scored",
        "detail": {
          "matched": 7,
          "missing": 4
        }
      }
    ],
    "parse": {
      "status": "ok",
      "columns": [
        1
      ],
      "unclickable_urls": [],
      "invisible_annotation_count": 2
    },
    "contact_links": {
      "summary": "Contact & Links: 0 issues found",
      "issue_count": 0,
      "phones": [
        {
          "raw": "+91 8081182505",
          "is_valid": true,
          "e164": "+918081182505",
          "issue": null
        }
      ],
      "emails": [
        {
          "raw": "Prateekpsingh5116548@gmail.com",
          "is_valid_syntax": true,
          "is_deliverable": null,
          "issue": null
        }
      ],
      "links": [
        {
          "url": "https://prateekpsingh.vercel.app/",
          "status": "ok",
          "http_status": null,
          "platform_issue": null
        },
        {
          "url": "https://www.linkedin.com/in/prateekpsingh/",
          "status": "ok",
          "http_status": null,
          "platform_issue": null
        },
        {
          "url": "https://leetcode.com/u/PrateekPSingh/",
          "status": "ok",
          "http_status": null,
          "platform_issue": null
        },
        {
          "url": "https://github.com/PrateekPsingh/100_ACRE_",
          "status": "ok",
          "http_status": null,
          "platform_issue": null
        },
        {
          "url": "https://github.com/PrateekPsingh/100_ACRE_",
          "status": "ok",
          "http_status": null,
          "platform_issue": null
        },
        {
          "url": "https://github.com/PrateekPsingh/CacheBolt",
          "status": "ok",
          "http_status": null,
          "platform_issue": null
        },
        {
          "url": "https://github.com/PrateekPsingh/CacheBolt",
          "status": "ok",
          "http_status": null,
          "platform_issue": null
        }
      ],
      "missing": []
    }
  }
};
