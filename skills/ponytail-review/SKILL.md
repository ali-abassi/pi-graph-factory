---
name: factory-ponytail-review
description: Review the integrated diff for unnecessary code and dependencies.
---

Trace the changed flow before judging it. Look for code that can be deleted,
existing project behavior that should be reused, standard-library or native
features replacing custom machinery, already-installed dependencies replacing
new ones, single-product factories, one-implementation interfaces, delegating
wrappers, dead flags, and speculative configuration.

Raise a blocking issue only when the unnecessary complexity is concrete: name
the exact files, what should be cut, and the smaller replacement. Do not trade
away correctness, validation, error handling, security, accessibility, approved
behavior, or the smallest meaningful test. This is a minimality lens inside the
normal correctness/security/evidence review, not a substitute for that review.

Adapted from Ponytail's MIT-licensed review discipline:
https://github.com/DietrichGebert/ponytail
