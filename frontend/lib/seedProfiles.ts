import type { PatientProfile } from "./types";

export interface SeedProfile extends PatientProfile {
  label: string;
  blurb: string;
}

// One-click profiles for instant demoing. Conditions match the cached corpora.
export const SEED_PROFILES: SeedProfile[] = [
  {
    label: "Metastatic HER2+ breast cancer",
    blurb: "54-year-old woman in San Jose, prior chemo",
    age: 54,
    sex: "female",
    condition: "breast cancer",
    location: "San Jose, California",
    priorTreatments: ["chemotherapy", "trastuzumab"],
    notes: "HER2-positive, metastatic to bone. Looking for targeted therapy trials.",
  },
  {
    label: "Pediatric epilepsy",
    blurb: "9-year-old with drug-resistant seizures",
    age: 9,
    sex: "male",
    condition: "epilepsy",
    location: "Boston, Massachusetts",
    priorTreatments: ["levetiracetam", "valproate"],
    notes: "Drug-resistant focal seizures despite two anti-seizure medications.",
  },
  {
    label: "Type 2 diabetes",
    blurb: "61-year-old, poor glucose control",
    age: 61,
    sex: "female",
    condition: "type 2 diabetes",
    location: "Houston, Texas",
    priorTreatments: ["metformin"],
    notes: "A1C around 8.4 on metformin. Open to new medication or device trials.",
  },
];
