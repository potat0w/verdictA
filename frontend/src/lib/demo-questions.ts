export type DemoQuestion = {
  id: string;
  label: string;
  query: string;
  category: "constitutional";
};

/** Demo prompts grounded in the Constitution of Bangladesh (not foreign law). */
export const DEMO_QUESTIONS: DemoQuestion[] = [
  {
    id: "equality-27",
    label: "Equality before law",
    query:
      "What does Article 27 of the Constitution of Bangladesh say about equality before the law?",
    category: "constitutional",
  },
  {
    id: "discrimination-28",
    label: "Discrimination",
    query:
      "Does the Constitution of Bangladesh prohibit discrimination on grounds of religion, race, caste, sex or place of birth?",
    category: "constitutional",
  },
  {
    id: "freedom-speech-39",
    label: "Freedom of speech",
    query:
      "What does Article 39 say about freedom of thought, conscience and speech in Bangladesh?",
    category: "constitutional",
  },
  {
    id: "assembly-37",
    label: "Peaceful assembly",
    query:
      "What is the right to assemble peacefully under Article 37 of the Bangladesh Constitution?",
    category: "constitutional",
  },
  {
    id: "arrest-33",
    label: "Safeguards on arrest",
    query:
      "What safeguards does Article 33 of the Constitution of Bangladesh give a person who is arrested?",
    category: "constitutional",
  },
  {
    id: "protection-life-32",
    label: "Right to life",
    query:
      "What does Article 32 say about protection of the right to life and personal liberty in Bangladesh?",
    category: "constitutional",
  },
  {
    id: "religion-41",
    label: "Freedom of religion",
    query:
      "What does Article 41 of the Bangladesh Constitution say about freedom of religion?",
    category: "constitutional",
  },
  {
    id: "property-42",
    label: "Right to property",
    query:
      "Can the government acquire private property in Bangladesh, and what does Article 42 say about compensation?",
    category: "constitutional",
  },
  {
    id: "enforcement-44",
    label: "Enforcing rights",
    query:
      "How can a citizen enforce fundamental rights under Article 44 of the Constitution of Bangladesh?",
    category: "constitutional",
  },
  {
    id: "law-vs-constitution",
    label: "Law vs Constitution",
    query:
      "If a law conflicts with the Constitution of Bangladesh, what happens to that law?",
    category: "constitutional",
  },
  {
    id: "writ-102",
    label: "High Court writs",
    query:
      "What powers does the High Court Division have under Article 102 to protect fundamental rights in Bangladesh?",
    category: "constitutional",
  },
  {
    id: "citizenship-6",
    label: "Citizenship",
    query:
      "What does the Constitution of Bangladesh say about citizenship of Bangladesh?",
    category: "constitutional",
  },
];

export const QUICK_SUGGESTIONS = [
  "What does Article 27 say about equality before the law?",
  "What safeguards does Article 33 give on arrest?",
  "What are the fundamental rights in the Bangladesh Constitution?",
  "If a Bangladeshi law conflicts with the Constitution, what happens?",
  "সংবিধানের ২৭ অনুচ্ছেদে সমতা সম্পর্কে কী বলা আছে?",
  "গ্রেপ্তারের সময় ৩৩ অনুচ্ছেদের সুরক্ষা কী?",
  "বাংলাদেশের সংবিধানে মৌলিক অধিকারগুলো কী কী?",
  "আইন সংবিধানের সাথে সাংঘর্ষিক হলে কী হয়?",
];
