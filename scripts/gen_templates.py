"""Prompt templates shared by data building and generation."""
QA_TEMPLATE = ("Answer the customer's question using only the RBI information below. "
               "If the information does not contain the answer, say that you don't know.\n\n"
               "RBI information:\n{context}\n\nQuestion: {question}")
QA_TEMPLATE_HI = ("नीचे दी गई RBI जानकारी का उपयोग करके ही ग्राहक के प्रश्न का उत्तर दें। "
                  "यदि जानकारी में उत्तर नहीं है, तो कहें कि आपको नहीं पता।\n\n"
                  "RBI जानकारी:\n{context}\n\nप्रश्न: {question}")

NOT_FOUND_EN = "The information provided does not answer this question, so I don't know. Please check with your bank or the RBI website."
NOT_FOUND_HI = "दी गई जानकारी में इस प्रश्न का उत्तर नहीं है, इसलिए मुझे नहीं पता। कृपया अपने बैंक या RBI की वेबसाइट से पुष्टि करें।"
