# RBI website terms: can we republish extracted FAQs?

**Verdict: unclear, leaning no without permission.** The site has no licence for reuse or republication, no open-data statement, and no explicit ban on copying the FAQ text either. What it does say is all-rights-reserved plus a ban on 'caching' the site's contents. Do not assume republishing on Hugging Face is allowed.

Not legal advice. Pages read on 2026-11-12.

## Exact sentences

- https://www.rbi.org.in/Scripts/Disclaimer.aspx
  > Every effort has been made to ensure the figures are correct. In case of doubt, however please check the print versions.
- https://www.rbi.org.in/Scripts/Disclaimer.aspx
  > The contents of this Web Site are provided on an "as is" basis without warranties of any kind.
- https://www.rbi.org.in/Scripts/Disclaimer.aspx
  > The contents on this Web Site do not constitute financial or other professional advice.
- https://www.rbi.org.in/Scripts/Disclaimer.aspx
  > Except as set forth below, caching and links to, and the framing of this Web Site or any of the contents are prohibited.
- https://www.rbi.org.in/Scripts/Disclaimer.aspx
  > © Reserve Bank of India. All Rights Reserved.
- https://www.rbi.org.in/commonman/English/Scripts/Disclaimer.aspx
  > © Reserve Bank of India. All Rights Reserved.

## What each says

- Footer on every page, including the FAQ pages: all rights reserved. No Creative Commons or other licence is named anywhere I found.
- The 'caching ... prohibited' sentence sits in the section on links to the site from other sites. It is about linking and framing, but its wording ('caching', 'any of the contents') could be read to cover keeping copies of content. Unclear.
- The disclaimer says the content is provided as is, may be inaccurate, and is not professional advice. Any dataset card should say the answers are RBI text as of the retrieval date, not advice.
- Nothing in the disclaimer or the Communication Policy page grants or refuses permission to reproduce text. A keyword scan of the three pages for copyright / reproduce / republish / redistribute / licence / reuse / permission / attribution found only:

  - https://www.rbi.org.in/commonman/English/Scripts/Disclaimer.aspx: permission
  - https://www.rbi.org.in/Scripts/Disclaimer.aspx: permission
  - https://www.rbi.org.in/Scripts/CommunicationPolicy.aspx: nothing

The 'permission' hit is the sentence about hyper-linking and framing, not about reuse.

## Other observations

- `https://www.rbi.org.in/robots.txt` returned HTTP 418 ('Unauthorised Access') to a browser-UA request on 2026-11-12, so crawl rules could not be read. The FAQ pages themselves returned 200. Not worked around.
- The Hindi disclaimer page (commonman/Hindi) is mostly in a legacy font and unreadable, so only the English text was used.

## Options if you want to publish

1. Ask RBI in writing for permission (contact address on the main site: helpdoc[at]rbi[dot]org[dot]in).
2. Publish the script and a pointer to the source URLs, not the text. Anyone can rebuild the set with `python3 scripts/fetch_rbi.py`.
3. If you publish text anyway, keep it to a small excerpt with the source URL, retrieval date, and 'Source: Reserve Bank of India' on every row, and state the licence status as unresolved in the dataset card.
