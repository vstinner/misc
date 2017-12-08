TODO:

* Clarify that some contributors are fine to contribute without being core
  developers.


[RFC: Process to become a core developer]

Hi,

I'm working on a process to describe how a contributor becomes a core developer. The purpose is to be transparent, list "requirements" and responsabilities to the contributor, and have written rules to help to take a fair decision.

This document is a draft. I chose to post it on python-committers. I expect that we would have to iterate on it multiple times until we can reach a consensus to agree on the process.

While the process has many details, it must be seen more as a guideline than strict rules.


== Introduction ==

The overall goal is to get more active developers working on Python to better scale horizontally: get more reviews to get better changes. The code quality is expected to be enhanced: more eyes on reviews should help to catch bugs earlier. Another less important goal is to speed up the Python development

IMHO the current blocker issue is that it is too hard to become a core developer. While becoming a core developer is not required to contribute, in my experience, core developers feel more involved and better recognized for their work. Core developer first means becoming responsible of a change: maintain the code/documentation and handle any potential regression. Long term commitment and good quality reviews are also expected from core developers.

The blocker issue can be explained by the very high step that should be climed at once to become a core developer. The contributor responsibilities changes at once from "no power" to "can do anything on any part of the project". A promotion is decided with a vote. If a voter doesn't know the contributor, it can be very stressful to take a decision. Building a trust relationship takes time and is not currently formalized by a process. This process is trying to address these issues.

I propose to formalize a process to promote a contributor from the early newcomer step to the final core developer step. The process is made of multiple steps to help the contributor to estimate their own progress. Mentoring becomes required by the process and is a major part of the whole process. While the process explains how to "clim" steps, going backward now becomes part of the process, it is not seen as a failure but as a normal and expected change under certain conditions. The final vote to promote a contributor as a core developer is expected to become more natural and simpler. The voters are expected to know better the future candidate.


== Process Steps ==

I propose the following steps to become a core developer:

* Step 0: Newcomer
* Step 1: Contributor
* Step 2: Bug triage permission
* Step 3: Mentoree.
* Step 4: Core developer


== Step 0: Newcomer ==

The first step is to start as a newcomer. Usually, newcomers are following the Python development without actively contributing.


== Step 1: Contributor ==

I consider that newcomers become automatically contributors as soon as they post their first comment on the bug tracker, comment on a pull request, or a pull request.

Their is no manual validation, nor additional privilege. It's just a thin distinction with a newcomer.

At this step, it becomes interesting to start reading the Python Developer Guide:
http://devguide.python.org/


== Step 2: Bug Triage Permission ==

Once a contributor becomes active enough, a core developer can propose to give the bug triage permission to the contributor. The contributors may ask themself to give this permission. The level of activity is not strictly defined, since it depends on the kind of contributions and their quality. The core developer is responsabile to estimate this.

There is no formal vote to give the bug triage permission. The core developer becomes responsible of the promotion. In practice, core developers are free to discuss together ;-)

Getting the bug triage permission gives more responsabilities to the contributor: the bug tracker should not be misused to not lost useful information. Taking a decision on an issue requires a certain level of knowledege of the Python development.

I propose that the contributor gets a mentor during one month. The role of the mentor is to answer to any question of the mentoree, and help them to take decisions if needed. The mentor is not expected to watch closely what the contributor does on the bug tracker.

If the contributor misuses the bug tracker, the mentor (or another core developer) should help the contributor to adjust their behaviour. If the contributor continue to abuse the bug tracker or misbehaves, the permission is removed and the contributor moves back to the previous step.

This step is the opportunity to know each other, begin to create a trust relationship.

Required skills for the contributor:

* Be active on the Python project: bug tracker, pull requests and/or mailing lists like python-ideas and python-dev. There is no minimum number of contributions: it's not a matter of quantity, but more a matter of quality and the kind of contributions.
* Be nice, police and respectful.
* Know what they are talking about, and explain their reasoning well.

Skills which are nice to have, but not required:

* Know how to triage bugs. If the contributor doesn't know that, I consider that the role of the mentor is to explain this (using the devguide documentation).

* Read the Python Developer Guide.

This step is also a first milestone to measure the contrbutor involvment in the Python project, to later be able to estimate their "longterm commitement".


== Step 3: Getting a mentor ==

Python project is big and has a long history. Contributors need a referrer to guide them in this wild and dangerous (!) project, and in the development workflow.

The role of the mentor is to answer to contributors questions and review their work. The role is not to become the single gatekeeper merging all contributions of one specific contributor. It's perfectly fine if the mentor is unable to review a pull request, just help to find an appropriate reviewer in this case.

This step is a second opportunity to build a trust relationship, maybe already started at the previous step with the same mentor.

Required contributor skills:

* Be active on the Python project: I would like to say "still" be active on the Python project, which is another proof of the contributor commitement in the project
* Sign the CLA: at some point, getting changes merged into Git becomes mandatory, and so the CLA must be signed.
* Find a mentor.

Required mentor skills:

* Be a core contributor.
* Be available at least during one whole month.
* Follow the contributor: must get an update at least once a week, especially if the contributor doesn't show up.

Obviously, it's better if the contributor interest areas match with the mentor interest areas ;-)

(... Maybe later we may change the process to allow non-core developers to become mentors, but I'm not sure about of this yet ...)

If the contributor becomes unavailable, it's fine, it's just a small step backward, until they become available again.

If the mentor becomes unavailable, maybe a different mentor can continue the process, otherwise the contributor goes back to the previous step.


== Step 4: Core Developer ==

Once the mentor or another core developer consider that the contributor is mature enough to be promoted, a vote is organized on the python-committers mailing list. The contributor skills and contributions should be listed. Usually, any negative vote becomes a veto which blocks the promotion.

While a few votes were negative in the past, I hope that this new formalized process would make the vote more natural and limit the "risk" of negative votes.

Requirements to become a core developer:

* Be nice and respectful
* Humility
* Long term commitement
* Reviews
* Know the CPython workflow
* Know the CPython lifecycle
* Know the Python C API specific issues, for contributors working on the C code
* Good quality patches

I described these requirements in detail at:
http://cpython-core-tutorial.readthedocs.io/en/latest/core_developer.html#requirements-to-become-a-core-developer

Becoming a core developer involves getting more responsabilities:

* The core developer becomes the "owner" of a merged change: maintain the code and handle any potential regression
* Review pull requests
* Triage bugs

The newly promoted core developer will followed by a mentor during one month until they become confortable enough. Obviously, the mentoring can be extended if needed.

If the result of the promotion vote is negative, it's ok, move back to the previous step, and retry later. Usually the vote can be retried 6 months later, time spent to address lacking skills (maybe with a mentor).

Hum, it seems like the contributor has been promoted: congratulations and welcome aboard!

Victor
