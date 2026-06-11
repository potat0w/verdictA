export type DemoQuestion = {
  id: string;
  label: string;
  query: string;
  category: "general" | "constitutional";
};

export const DEMO_QUESTIONS: DemoQuestion[] = [
  {
    id: "defamation-social",
    label: "False info on social media",
    query:
      "If I post false information about someone on social media, can I be sued?",
    category: "general",
  },
  {
    id: "arrest-warrant",
    label: "Arrest without a warrant",
    query:
      "If the police arrest me without showing a warrant, what are my rights?",
    category: "general",
  },
  {
    id: "free-speech",
    label: "Criticizing the government",
    query:
      "If I criticize the government publicly, am I protected by freedom of speech?",
    category: "constitutional",
  },
  {
    id: "religious-discrimination",
    label: "Fired because of religion",
    query: "If a company fires me because of my religion, is that legal?",
    category: "general",
  },
  {
    id: "tax-refusal",
    label: "Refusing to pay taxes",
    query: "If I refuse to pay taxes, what legal consequences can I face?",
    category: "general",
  },
  {
    id: "privacy-messages",
    label: "Private messages accessed",
    query:
      "If my private messages are accessed without my permission, has my constitutional right to privacy been violated?",
    category: "constitutional",
  },
  {
    id: "police-search",
    label: "Police stop and search",
    query: "If I am stopped and searched by the police, can I refuse?",
    category: "general",
  },
  {
    id: "peaceful-protest",
    label: "Protest without permission",
    query:
      "If I participate in a peaceful protest without permission, can I be arrested?",
    category: "constitutional",
  },
  {
    id: "equality-law",
    label: "Unequal treatment by law",
    query:
      "If a law treats one group of citizens differently from another, does it violate the principle of equality before the law?",
    category: "constitutional",
  },
  {
    id: "right-to-silence",
    label: "Right to remain silent",
    query: "If I am accused of a crime, do I have the right to remain silent?",
    category: "constitutional",
  },
  {
    id: "property-compensation",
    label: "Government takes property",
    query:
      "If the government takes my property for a public project, am I entitled to compensation?",
    category: "constitutional",
  },
  {
    id: "gender-admission",
    label: "Denied admission by gender",
    query:
      "If I am denied admission to a public institution because of my gender, can I challenge the decision legally?",
    category: "constitutional",
  },
  {
    id: "copyright-sharing",
    label: "Sharing copyrighted content",
    query:
      "If I share copyrighted content online without permission, what penalties could I face?",
    category: "general",
  },
  {
    id: "detention-without-court",
    label: "Detained without court hearing",
    query:
      "If I am detained for several days without being brought before a court, are my constitutional rights being violated?",
    category: "constitutional",
  },
  {
    id: "information-access",
    label: "Denied public information",
    query:
      "If a public authority refuses to provide information that I am legally entitled to access, what can I do?",
    category: "general",
  },
  {
    id: "violate-fundamental-rights",
    label: "Violating fundamental rights",
    query:
      "If I violate someone's fundamental rights, what legal action can they take against me?",
    category: "constitutional",
  },
  {
    id: "gov-violates-rights",
    label: "Government violates rights",
    query:
      "If the government violates a citizen's constitutional rights, what remedies are available?",
    category: "constitutional",
  },
  {
    id: "law-vs-constitution",
    label: "Law vs Constitution",
    query: "If a law conflicts with the Constitution, what happens to that law?",
    category: "constitutional",
  },
  {
    id: "challenge-expression",
    label: "Restricted freedom of expression",
    query:
      "If my freedom of expression is restricted, how can I challenge that decision?",
    category: "constitutional",
  },
  {
    id: "unconstitutional-action",
    label: "Unconstitutional government action",
    query:
      "If I believe a government action is unconstitutional, where can I seek justice?",
    category: "constitutional",
  },
];

export const QUICK_SUGGESTIONS = [
  DEMO_QUESTIONS.find((q) => q.id === "right-to-silence")!,
  DEMO_QUESTIONS.find((q) => q.id === "free-speech")!,
  DEMO_QUESTIONS.find((q) => q.id === "arrest-warrant")!,
  DEMO_QUESTIONS.find((q) => q.id === "law-vs-constitution")!,
];
