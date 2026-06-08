/* ============================================================================
   MOUMI - AI Mascot Companion for Mouverse AI
   Emotional Intelligence, Multilingual Support, Smart Personality
   ============================================================================ */

const MOUMI = {
  // Current state
  currentState: 'idle',
  
  // User preferences memory
  userPreferences: {
    genres: [],
    languages: [],
    ratings: [],
    searches: [],
    reviews: [],
    moodHistory: []
  },
  
  // Language detection patterns
  languagePatterns: {
    english: /\b(the|is|are|was|were|have|has|had|will|would|could|should|may|might|must|can|need|want|like|love|hate|happy|sad|excited|good|bad|great|awesome|terrible)\b/i,
    bengali: /[\u0980-\u09FF]/,
    hindi: /[\u0900-\u097F]/,
    tamil: /[\u0B80-\u0BFF]/,
    telugu: /[\u0C00-\u0C7F]/,
    malayalam: /[\u0D00-\u0D7F]/,
    kannada: /[\u0C80-\u0CFF]/,
    marathi: /[\u0900-\u097F]/,
    punjabi: /[\u0A00-\u0A7F]/
  },
  
  // Enhanced multilingual responses with reasoning
  responses: {
    english: {
      welcome: "Welcome back {name}! 😊🍿",
      welcome_new: "Hi {name}! I'm Moumi, your movie companion! 🎬",
      happy: "I'm so happy for you! Let's find some uplifting movies! 😊",
      sad: "I understand you're feeling down. Sometimes a comforting movie helps. Let me suggest something gentle to lift your spirits. 💙",
      excited: "Your excitement is contagious! Time for some thrilling movies that match your energy! 🤩",
      romantic: "Love is in the air! Here are some romantic picks perfect for the mood. ❤️",
      thrilling: "Ready for some adrenaline? These movies will keep you on the edge of your seat! 😱",
      motivated: "Let's fuel that motivation with inspiring stories that'll keep you going! 💪",
      dark: "For when you want something intense and thought-provoking. These films will make you think. 🌑",
      funny: "Laughter is the best medicine! Here are some comedies to brighten your day! 😂",
      stressed: "I can tell you need a break. Let me find some relaxing films to help you unwind. 😌",
      curious: "Great question! Let me explore some interesting options for you. 🤔",
      nostalgic: "Ah, the classics! Let me find some films that'll take you back. 📷",
      recommendation: "Based on what you've told me, I found some movies that might be perfect for you! 🎬✨",
      thinking: "Let me think about the best options for you... 🤔",
      greeting: "Hello! I'm Moumi, your AI movie companion. How can I help you discover great films today? 😊",
      emotional_not_sad: "I understand - you want something emotional but not too heavy. Let me find hopeful dramas and inspiring stories that'll touch your heart without bringing you down. 💙",
      relaxing: "Perfect choice! Let me find some calming, peaceful films to help you relax. 😌",
      uplifting: "Wonderful! I'll look for inspiring, feel-good movies that'll leave you feeling positive. ✨",
      thought_provoking: "Excellent! Let me find some intellectually stimulating films that'll make you think. 🧠"
    },
    bengali: {
      welcome: "স্বাগতম {name}! 😊🍿",
      welcome_new: "হ্যালো {name}! আমি মৌমি, তোমার সিনেমা সঙ্গী! 🎬",
      happy: "তোমার জন্য খুশি! কিছু ভালো সিনেমা দেখি! 😊",
      sad: "বুঝতে পারছি তুমি খারাপ বোধ করছ। কিছু আরামদায়ক সিনেমা দেখবে? 💙",
      excited: "তোমার উত্তেজনা সংক্রামক! থ্রিলার সিনেমা দেখি! 🤩",
      romantic: "ভালোবাসা বাতাসে! রোমান্টিক সিনেমা দেখি! ❤️",
      thrilling: "রোমাঞ্চের জন্য প্রস্তুত! 😱",
      motivated: "অনুপ্রেরণামূলক গল্প দেখি! 💪",
      dark: "গভীর চিন্তার জন্য। 🌑",
      funny: "হাসি সেরা ওষুধ! কমেডি দেখি! 😂",
      stressed: "বুঝতে পারছি তুমি বিশ্রাম দরকার। কিছু শান্ত সিনেমা দেখি! 😌",
      curious: "চমৎকার প্রশ্ন! কিছু আকর্ষণীয় সিনেমা দেখি! 🤔",
      nostalgic: "আহ, ক্লাসিক! কিছু পুরনো সিনেমা দেখি! 📷",
      recommendation: "তোমার কথা শুনে কিছু সিনেমা পেয়েছি! 🎬✨",
      thinking: "ভাবছি... 🤔",
      greeting: "নমস্কার! আমি মৌমি, তোমার সিনেমা সঙ্গী। আজ কীভাবে সাহায্য করতে পারি? 😊",
      emotional_not_sad: "বুঝতে পারছি - তুমি আবেগিক কিন্তু খুব ভারী চাও না। আশাবাদী নাটক দেখি! 💙",
      relaxing: "চমৎকার পছন্দ! কিছু শান্ত সিনেমা দেখি! 😌",
      uplifting: "চমৎকার! অনুপ্রেরণামূলক সিনেমা দেখি! ✨",
      thought_provoking: "চমৎকার! চিন্তাশীল সিনেমা দেখি! 🧠"
    },
    hindi: {
      welcome: "वापसी पर स्वागत है {name}! 😊🍿",
      welcome_new: "नमस्ते {name}! मैं मौमी हूं, आपका फिल्म साथी! 🎬",
      happy: "आपके लिए खुश! कुछ अच्छी फिल्में देखते हैं! 😊",
      sad: "समझ गया आप उदास हैं। कुछ आरामदायक फिल्में देखेंगे? 💙",
      excited: "आपका उत्साह संक्रामक है! थ्रिलर फिल्में देखते हैं! 🤩",
      romantic: "प्यार हवा में है! रोमांटिक फिल्में देखते हैं! ❤️",
      thrilling: "रोमांच के लिए तैयार! 😱",
      motivated: "प्रेरणादायक कहानियां देखते हैं! 💪",
      dark: "गहरी सोच के लिए। 🌑",
      funny: "हंसी सबसे अच्छी दवा है! कॉमेडी देखते हैं! 😂",
      stressed: "समझ गया आपको आराम चाहिए। शांत फिल्में देखते हैं! 😌",
      curious: "बढ़िया प्रश्न! कुछ दिलचस्प फिल्में देखते हैं! 🤔",
      nostalgic: "आह, क्लासिक! कुछ पुरानी फिल्में देखते हैं! 📷",
      recommendation: "आपकी बात सुनकर कुछ फिल्में मिलीं! 🎬✨",
      thinking: "सोच रहा हूं... 🤔",
      greeting: "नमस्ते! मैं मौमी हूं, आपका फिल्म साथी। आज कैसे मदद कर सकता हूं? 😊",
      emotional_not_sad: "समझ गया - आप भावनात्मक लेकिन बहुत भारी नहीं चाहते। आशावादी नाटक देखते हैं! 💙",
      relaxing: "बढ़िया विकल्प! शांत फिल्में देखते हैं! 😌",
      uplifting: "बढ़िया! प्रेरणादायक फिल्में देखते हैं! ✨",
      thought_provoking: "बढ़िया! बौद्धिक फिल्में देखते हैं! 🧠"
    },
    tamil: {
      welcome: "மீண்டும் வரவேற்கிறேன் {name}! 😊🍿",
      welcome_new: "வணக்கம் {name}! நான் மௌமி, உங்கள் திரைப்பட தோழர்! 🎬",
      happy: "உங்களுக்கு மகிழ்ச்சி! சில நல்ல திரைப்படங்கள் பார்க்கலாம்! 😊",
      sad: "புரிகிறது நீங்கள் சோர்வாக உள்ளீர்கள். சில ஆறுதல் திரைப்படங்கள் பார்க்கலாமா? 💙",
      excited: "உங்கள் உற்சாகம் தொற்றுநோய்! திரில்லர் படங்கள் பார்க்கலாம்! 🤩",
      romantic: "காதல் காற்றில்! ரொமான்டிக் படங்கள் பார்க்கலாம்! ❤️",
      thrilling: "உற்சாகத்திற்கு தயார்! 😱",
      motivated: "ஈர்ப்புள்ள கதைகள் பார்க்கலாம்! 💪",
      dark: "ஆழமான சிந்தனைக்கு। 🌑",
      funny: "சிரிப்பு சிறந்த மருந்து! நகைச்சுவை பார்க்கலாம்! 😂",
      stressed: "புரிகிறது உங்களுக்கு ஓய்வு தேவை. அமைதியான படங்கள் பார்க்கலாம்! 😌",
      curious: "அருமையான கேள்வி! சில விசித்திரமான படங்கள் பார்க்கலாம்! 🤔",
      nostalgic: "ஆஹா, கிளாசிக்! சில பழைய படங்கள் பார்க்கலாம்! 📷",
      recommendation: "உங்கள் பேச்சைக் கேட்டு சில படங்கள் கிடைத்தன! 🎬✨",
      thinking: "யோசிக்கிறேன்... 🤔",
      greeting: "வணக்கம்! நான் மௌமி, உங்கள் திரைப்பட தோழர். இன்று எப்படி உதவ முடியும்? 😊",
      emotional_not_sad: "புரிகிறது - நீங்கள் உணர்ச்சிகரமானது ஆனால் மிகவும் கனமானது அல்ல. நம்பிக்கையான நாடகங்கள் பார்க்கலாம்! 💙",
      relaxing: "சிறந்த தேர்வு! அமைதியான படங்கள் பார்க்கலாம்! 😌",
      uplifting: "அருமையானது! ஈர்ப்பூட்டும் படங்கள் பார்க்கலாம்! ✨",
      thought_provoking: "அருமையானது! அறிவார்ந்த படங்கள் பார்க்கலாம்! 🧠"
    },
    telugu: {
      welcome: "మళ్లీ స్వాగతం {name}! 😊🍿",
      welcome_new: "హలో {name}! నేను మౌమి, మీ సినిమా స్నేహితుడు! 🎬",
      happy: "మీకు సంతోషం! కొన్ని మంచి సినిమాలు చూద్దాం! 😊",
      sad: "అర్థమైంది మీరు బాధగా ఉన్నారు. కొన్ని సౌకర్యవంతమైన సినిమాలు చూద్దామా? 💙",
      excited: "మీ ఉత్సాహం సంక్రమణ! థ్రిల్లర్ సినిమాలు చూద్దాం! 🤩",
      romantic: "ప్రేమ గాలిలో! రొమాంటిక్ సినిమాలు చూద్దాం! ❤️",
      thrilling: "ఉత్సాహానికి సిద్ధం! 😱",
      motivated: "స్ఫూర్తిదాయక కథలు చూద్దాం! 💪",
      dark: "లోతైన ఆలోచనకు। 🌑",
      funny: "నవ్వు ఉత్తమ మందు! కామెడీ చూద్దాం! 😂",
      stressed: "అర్థమైంది మీకు విశ్రాంతి కావాలి. శాంతమైన సినిమాలు చూద్దాం! 😌",
      curious: "గొప్ప ప్రశ్న! కొన్ని ఆకర్షణీయమైన సినిమాలు చూద్దాం! 🤔",
      nostalgic: "ఆహా, క్లాసిక్! కొన్ని పాత సినిమాలు చూద్దాం! 📷",
      recommendation: "మీ మాటలు విని కొన్ని సినిమాలు దొరికాయి! 🎬✨",
      thinking: "ఆలోచిస్తున్నా... 🤔",
      greeting: "హలో! నేను మౌమి, మీ సినిమా స్నేహితుడు. ఈరోజు ఎలా సహాయం చేయగలను? 😊",
      emotional_not_sad: "అర్థమైంది - మీరు భావోద్వేగం కానీ చాలా భారీ కాదు. ఆశావహమైన నాటకాలు చూద్దాం! 💙",
      relaxing: "గొప్ప ఎంపిక! శాంతమైన సినిమాలు చూద్దాం! 😌",
      uplifting: "గొప్పమైనది! స్ఫూర్తిదాయక సినిమాలు చూద్దాం! ✨",
      thought_provoking: "గొప్పమైనది! బుద్ధివంతమైన సినిమాలు చూద్దాం! 🧠"
    },
    malayalam: {
      welcome: "വീണ്ടും സ്വാഗതം {name}! 😊🍿",
      welcome_new: "ഹലോ {name}! ഞാൻ മൗമി, നിങ്ങളുടെ സിനിമാ സുഹൃത്ത്! 🎬",
      happy: "നിങ്ങൾക്ക് സന്തോഷം! ചില നല്ല സിനിമകൾ കാണാം! 😊",
      sad: "മനസ്സിലായി. ചില ആശ്വാസകരമായ സിനിമകൾ കാണാമോ? 💙",
      excited: "നിങ്ങളുടെ ഉത്സാഹം പകർച്ച! ത്രില്ലർ സിനിമകൾ കാണാം! 🤩",
      romantic: "പ്രണയം കാറ്റിൽ! റൊമാന്റിക് സിനിമകൾ കാണാം! ❤️",
      thrilling: "ഉത്സാഹത്തിന് തയ്യാറായി! 😱",
      motivated: "പ്രചോദനാത്മകമായ കഥകൾ കാണാം! 💪",
      dark: "ആഴത്തെ ചിന്തയ്ക്ക്। 🌑",
      funny: "ചിരി മികച്ച മരുന്ന്! കോമഡി കാണാം! 😂",
      stressed: "മനസ്സിലായി നിങ്ങൾക്ക് വിശ്രമം വേണ്ടി. ശാന്തമായ സിനിമകൾ കാണാം! 😌",
      curious: "മികച്ച ചോദ്യം! ചില ആകർഷണീയമായ സിനിമകൾ കാണാം! 🤔",
      nostalgic: "ആഹാ, ക്ലാസിക്! ചില പഴയ സിനിമകൾ കാണാം! 📷",
      recommendation: "നിങ്ങളുടെ സംസാരം കേട്ടു ചില സിനിമകൾ കിട്ടി! 🎬✨",
      thinking: "ചിന്തിക്കുന്നു... 🤔",
      greeting: "ഹലോ! ഞാൻ മൗമി, നിങ്ങളുടെ സിനിമാ സുഹൃത്ത്. ഇന്ന് എങ്ങനെ സഹായിക്കാം? 😊",
      emotional_not_sad: "മനസ്സിലായി - നിങ്ങൾ ഭാവനാടകം എന്നാൽ വളരെ ഭാരി അല്ല. പ്രതീക്ഷയുള്ള നാടകങ്ങൾ കാണാം! 💙",
      relaxing: "മികച്ച തിരഞ്ഞെടുക്കൽ! ശാന്തമായ സിനിമകൾ കാണാം! 😌",
      uplifting: "മികച്ചമാണ്! പ്രചോദനാത്മകമായ സിനിമകൾ കാണാം! ✨",
      thought_provoking: "മികച്ചമാണ്! ബുദ്ധിപരമായ സിനിമകൾ കാണാം! 🧠"
    },
    kannada: {
      welcome: "ಮರು ಸ್ವಾಗತ {name}! 😊🍿",
      welcome_new: "ಹಲೋ {name}! ನಾನು ಮೌಮಿ, ನಿಮ್ಮ ಚಲನಚಿತ್ರ ಸ್ನೇಹಿತ! 🎬",
      happy: "ನಿಮಗೆ ಸಂತೋಷ! ಕೆಲವು ಉತ್ತಮ ಚಲನಚಿತ್ರಗಳನ್ನು ನೋಡೋಣ! 😊",
      sad: "ಅರ್ಥವಾಯಿತು. ಕೆಲವು ಆರಾಮದಾಯಕ ಚಲನಚಿತ್ರಗಳನ್ನು ನೋಡೋಣ? 💙",
      excited: "ನಿಮ್ಮ ಉತ್ಸಾಹ ಸಾಂಕ್ರಾಮಿಕ! ಥ್ರಿಲ್ಲರ್ ಚಲನಚಿತ್ರಗಳನ್ನು ನೋಡೋಣ! 🤩",
      romantic: "ಪ್ರೇಮ ಗಾಳಿಯಲ್ಲಿ! ರೊಮ್ಯಾಂಟಿಕ್ ಚಲನಚಿತ್ರಗಳನ್ನು ನೋಡೋಣ! ❤️",
      thrilling: "ಉತ್ಸಾಹಕ್ಕೆ ಸಿದ್ಧ! 😱",
      motivated: "ಪ್ರೇರಣಾದಾಯಕ ಕಥೆಗಳನ್ನು ನೋಡೋಣ! 💪",
      dark: "ಆಳವಾದ ಚಿಂತನೆಗೆ। 🌑",
      funny: "ನಗುವು ಉತ್ತಮ ಔಷಧ! ಹಾಸ್ಯ ನೋಡೋಣ! 😂",
      stressed: "ಅರ್ಥವಾಯಿತು ನಿಮಗೆ ವಿಶ್ರಾಂತಿ ಬೇಕು. ಶಾಂತ ಚಲನಚಿತ್ರಗಳನ್ನು ನೋಡೋಣ! 😌",
      curious: "ಉತ್ತಮ ಪ್ರಶ್ನೆ! ಕೆಲವು ಆಕರ್ಷಣೀಯ ಚಲನಚಿತ್ರಗಳನ್ನು ನೋಡೋಣ! 🤔",
      nostalgic: "ಆಹಾ, ಕ್ಲಾಸಿಕ್! ಕೆಲವು ಹಳೆಯ ಚಲನಚಿತ್ರಗಳನ್ನು ನೋಡೋಣ! 📷",
      recommendation: "ಕೆಲವು ಚಲನಚಿತ್ರಗಳು ಸಿಕ್ಕವು! 🎬✨",
      thinking: "ಯೋಚಿಸುತ್ತಿದ್ದೇನೆ... 🤔",
      greeting: "ಹಲೋ! ನಾನು ಮೌಮಿ, ನಿಮ್ಮ ಚಲನಚಿತ್ರ ಸ್ನೇಹಿತ. ಇಂದು ಹೇಗೆ ಸಹಾಯ ಮಾಡಬಹುದು? 😊",
      emotional_not_sad: "ಅರ್ಥವಾಯಿತು - ನೀವು ಭಾವನಾಟಕ ಆದರೆ ತುಂಬಾ ಭಾರಿ ಅಲ್ಲ. ಭರವಸೆಯ ನಾಟಕಗಳನ್ನು ನೋಡೋಣ! 💙",
      relaxing: "ಉತ್ತಮ ಆಯ್ಕೆ! ಶಾಂತ ಚಲನಚಿತ್ರಗಳನ್ನು ನೋಡೋಣ! 😌",
      uplifting: "ಉತ್ತಮವಾದದ್ದು! ಪ್ರೇರಣಾದಾಯಕ ಚಲನಚಿತ್ರಗಳನ್ನು ನೋಡೋಣ! ✨",
      thought_provoking: "ಉತ್ತಮವಾದದ್ದು! ಬುದ್ಧಿವಂತ ಚಲನಚಿತ್ರಗಳನ್ನು ನೋಡೋಣ! 🧠"
    },
    marathi: {
      welcome: "परत स्वागत {name}! 😊🍿",
      welcome_new: "नमस्कार {name}! मी मौमी, तुमचा चित्रपट मित्र! 🎬",
      happy: "तुमच्यासाठी आनंद! काही चांगले चित्रपट बघूया! 😊",
      sad: "समजले. काही आरामदायक चित्रपट बघूया का? 💙",
      excited: "तुमचा उत्साह संक्रामक! थ्रिलर चित्रपट बघूया! 🤩",
      romantic: "प्रेम वाऱ्यात! रोमँटिक चित्रपट बघूया! ❤️",
      thrilling: "उत्साहासाठी तयार! 😱",
      motivated: "प्रेरणादायक कथा बघूया! 💪",
      dark: "खोल विचारांसाठी। 🌑",
      funny: "हसणे सर्वोत्तम औषध! कॉमेडी बघूया! 😂",
      stressed: "समजले तुम्हाला विश्रांती हवी आहे. शांत चित्रपट बघूया! 😌",
      curious: "उत्तम प्रश्न! काही आकर्षक चित्रपट बघूया! 🤔",
      nostalgic: "आह, क्लासिक! काही जुने चित्रपट बघूया! 📷",
      recommendation: "तुमची गोष्टी ऐकून काही चित्रपट सापडले! 🎬✨",
      thinking: "विचार करत आहे... 🤔",
      greeting: "नमस्कार! मी मौमी, तुमचा चित्रपट मित्र. आज कसे मदत करू? 😊",
      emotional_not_sad: "समजले - तुम्हाला भावनात्मक हवे पण खूप जड नाही. आशावादी नाटके बघूया! 💙",
      relaxing: "उत्तम निवड! शांत चित्रपट बघूया! 😌",
      uplifting: "उत्तम आहे! प्रेरणादायक चित्रपट बघूया! ✨",
      thought_provoking: "उत्तम आहे! बुद्धिमान चित्रपट बघूया! 🧠"
    },
    punjabi: {
      welcome: "ਵਾਪਸੀ ਤੇ ਜੀ ਆਇਆਂ ਨੂੰ {name}! 😊🍿",
      welcome_new: "ਸਤ ਸ੍ਰੀ ਅਕਾਲ {name}! ਮੈਂ ਮੌਮੀ, ਤੁਹਾਡਾ ਫਿਲਮ ਦੋਸਤ! 🎬",
      happy: "ਤੁਹਾਡੇ ਲਈ ਖੁਸ਼! ਕੁਝ ਚੰਗੀਆਂ ਫਿਲਮਾਂ ਵੇਖੀਏ! 😊",
      sad: "ਸਮਝ ਆਇਆ। ਕੁਝ ਆਰਾਮਦਾਇਕ ਫਿਲਮਾਂ ਵੇਖੀਏ? 💙",
      excited: "ਤੁਹਾਡਾ ਉਤਸ਼ਾਹ ਛੂਤ ਹੈ! ਥ੍ਰਿਲਰ ਫਿਲਮਾਂ ਵੇਖੀਏ! 🤩",
      romantic: "ਪਿਆਰ ਹਵਾ ਵਿੱਚ! ਰੋਮਾਂਟਿਕ ਫਿਲਮਾਂ ਵੇਖੀਏ! ❤️",
      thrilling: "ਉਤਸ਼ਾਹ ਲਈ ਤਿਆਰ! 😱",
      motivated: "ਪ੍ਰੇਰਣਾਦਾਇਕ ਕਹਾਣੀਆਂ ਵੇਖੀਏ! 💪",
      dark: "ਗੂੜੀ ਸੋਚ ਲਈ। 🌑",
      funny: "ਹੱਸਣਾ ਸਭ ਤੋਂ ਵਧੀਆ ਦਵਾਈ! ਕਾਮੇਡੀ ਵੇਖੀਏ! 😂",
      stressed: "ਸਮਝ ਆਇਆ ਤੁਹਾਨੂੰ ਆਰਾਮ ਚਾਹੀਦਾ ਹੈ। ਸ਼ਾਂਤ ਫਿਲਮਾਂ ਵੇਖੀਏ! 😌",
      curious: "ਵਧੀਆ ਸਵਾਲ! ਕੁਝ ਆਕਰਸ਼ਕ ਫਿਲਮਾਂ ਵੇਖੀਏ! 🤔",
      nostalgic: "ਆਹ, ਕਲਾਸਿਕ! ਕੁਝ ਪੁਰਾਣੀਆਂ ਫਿਲਮਾਂ ਵੇਖੀਏ! 📷",
      recommendation: "ਤੁਹਾਡੀ ਗੱਲ ਸੁਣ ਕੇ ਕੁਝ ਫਿਲਮਾਂ ਮਿਲੀਆਂ! 🎬✨",
      thinking: "ਸੋਚ ਰਿਹਾ ਹਾਂ... 🤔",
      greeting: "ਸਤ ਸ੍ਰੀ ਅਕਾਲ! ਮੈਂ ਮੌਮੀ, ਤੁਹਾਡਾ ਫਿਲਮ ਦੋਸਤ। ਅੱਜ ਕਿਵੇਂ ਮਦਦ ਕਰ ਸਕਦਾ ਹਾਂ? 😊",
      emotional_not_sad: "ਸਮਝ ਆਇਆ - ਤੁਸੀਂ ਭਾਵਨਾਤਮਕ ਚਾਹੁੰਦੇ ਹੋ ਪਰ ਬਹੁਤ ਭਾਰੀ ਨਹੀਂ। ਆਸ਼ਾਵਾਦੀ ਡਰਾਮੇ ਵੇਖੀਏ! 💙",
      relaxing: "ਵਧੀਆ ਚੋਣ! ਸ਼ਾਂਤ ਫਿਲਮਾਂ ਵੇਖੀਏ! 😌",
      uplifting: "ਵਧੀਆ! ਪ੍ਰੇਰਣਾਦਾਇਕ ਫਿਲਮਾਂ ਵੇਖੀਏ! ✨",
      thought_provoking: "ਵਧੀਆ! ਬੁੱਧੀਮਾਨ ਫਿਲਮਾਂ ਵੇਖੀਏ! 🧠"
    }
  },
  
  // Enhanced emotion detection with tone analysis
  emotionPatterns: {
    sad: {
      patterns: /\b(sad|depressed|unhappy|down|lonely|grief|cry|crying|tears|heartbreak|disappointed|miserable|hopeless|gloomy|upset|hurt|pain|loss|miss|broken)\b/i,
      intensity: 'high',
      response_type: 'supportive'
    },
    happy: {
      patterns: /\b(happy|joy|excited|great|awesome|wonderful|amazing|fantastic|love|delighted|thrilled|ecstatic|cheerful|glad|blessed|grateful)\b/i,
      intensity: 'high',
      response_type: 'enthusiastic'
    },
    excited: {
      patterns: /\b(excited|thrilled|pumped|can't wait|eager|enthusiastic|hyped|stoked|ready|looking forward)\b/i,
      intensity: 'high',
      response_type: 'energetic'
    },
    romantic: {
      patterns: /\b(love|romance|romantic|valentine|date|crush|relationship|heart|kiss|wedding|affection|passion)\b/i,
      intensity: 'medium',
      response_type: 'warm'
    },
    thrilling: {
      patterns: /\b(thrill|scary|horror|adrenaline|intense|action|suspense|edge|exciting|adventure|danger)\b/i,
      intensity: 'high',
      response_type: 'energetic'
    },
    motivated: {
      patterns: /\b(motivated|inspired|determined|ambitious|goal|success|achieve|push|drive|focus|work hard)\b/i,
      intensity: 'medium',
      response_type: 'encouraging'
    },
    dark: {
      patterns: /\b(dark|serious|intense|drama|tragic|heavy|deep|thought|philosophical|complex|meaningful)\b/i,
      intensity: 'medium',
      response_type: 'thoughtful'
    },
    funny: {
      patterns: /\b(funny|comedy|laugh|hilarious|joke|humor|fun|entertainment|lighthearted|silly)\b/i,
      intensity: 'medium',
      response_type: 'playful'
    },
    stressed: {
      patterns: /\b(stressed|anxious|worried|tense|overwhelmed|pressure|burnout|exhausted|tired|need break)\b/i,
      intensity: 'high',
      response_type: 'calming'
    },
    curious: {
      patterns: /\b(curious|wonder|interested|want to know|learn|explore|discover|find out)\b/i,
      intensity: 'low',
      response_type: 'informative'
    },
    nostalgic: {
      patterns: /\b(nostalgic|remember|childhood|old times|memories|classic|vintage|retro)\b/i,
      intensity: 'medium',
      response_type: 'warm'
    }
  },
  
  // Contextual reasoning patterns
  reasoningPatterns: {
    emotionalButNotSad: /\b(emotional|feeling|touching|moving) but not (sad|depressing|tragic|heavy)\b/i,
    relaxing: /\b(relaxing|calm|peaceful|soothing|chill|easy|comfort)\b/i,
    uplifting: /\b(uplifting|inspiring|hopeful|positive|feel good|motivating)\b/i,
    thoughtProvoking: /\b(thought provoking|intellectual|smart|clever|mind bending|complex)\b/i,
    familyFriendly: /\b(family friendly|kids|children|safe|appropriate for all ages)\b/i,
    short: /\b(short|quick|brief|under 2 hours|less than 2 hours)\b/i,
    long: /\b(long|epic|detailed|over 2 hours|more than 2 hours)\b/i
  },
  
  // Initialize Moumi
  async init() {
    this.loadUserPreferences();
    this.loadConversationMemory();
    await this.inlineAllMascotSVGs();
    this.initializeIntegratedMoumi();
    this.bindEvents();
    this.checkReturningUser();
  },

  // Inline all mascot SVGs to enable CSS styling/animations and DOM interaction
  async inlineAllMascotSVGs() {
    const images = document.querySelectorAll('img.moumi-character');
    const promises = Array.from(images).map(async (img) => {
      const src = img.getAttribute('src');
      if (!src) return;
      
      try {
        const res = await fetch(src);
        if (!res.ok) return;
        const text = await res.text();
        const parser = new DOMParser();
        const doc = parser.parseFromString(text, 'image/svg+xml');
        const svg = doc.querySelector('svg');
        if (!svg) return;
        
        // Copy classes, ID and style attributes
        if (img.id) svg.id = img.id;
        Array.from(img.attributes).forEach(attr => {
          if (attr.name !== 'src' && attr.name !== 'alt') {
            svg.setAttribute(attr.name, attr.value);
          }
        });
        
        img.replaceWith(svg);
      } catch (e) {
        console.error('[MOUMI] Failed to inline SVG:', e);
      }
    });
    
    await Promise.all(promises);
  },
  
  // Load user preferences from localStorage
  loadUserPreferences() {
    const saved = localStorage.getItem('moumi_preferences');
    if (saved) {
      try {
        this.userPreferences = JSON.parse(saved);
      } catch (e) {
        console.error('[MOUMI] Failed to load preferences:', e);
      }
    }
  },
  
  // Save user preferences to localStorage
  saveUserPreferences() {
    localStorage.setItem('moumi_preferences', JSON.stringify(this.userPreferences));
  },
  
  // Initialize integrated Moumi (FAB and header)
  initializeIntegratedMoumi() {
    // Load CSS
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = '/static/moumi.css';
    document.head.appendChild(link);
    
    // Set initial state for both Moumi instances
    const fabContainer = document.getElementById('moumiFabContainer');
    const headerContainer = document.getElementById('moumiHeaderContainer');
    
    if (fabContainer) {
      fabContainer.classList.add('moumi-state-idle');
    }
    
    if (headerContainer) {
      headerContainer.classList.add('moumi-state-idle');
    }
  },
  
  // Bind events
  bindEvents() {
    // Bind to FAB mascot character (inside the FAB button)
    const fabCharacter = document.getElementById('moumiFabCharacter');
    if (fabCharacter) {
      fabCharacter.addEventListener('mouseenter', () => this.onMoumiHover());
    }
    
    // Bind to header mascot character
    const headerCharacter = document.getElementById('moumiHeaderCharacter');
    if (headerCharacter) {
      headerCharacter.addEventListener('click', () => this.onMoumiClick());
    }
    
    // Listen for chat open/close
    const chatFab = document.getElementById('chatFab');
    if (chatFab) {
      chatFab.addEventListener('click', () => {
        const win = document.getElementById('chatWindow');
        if (win) {
          if (win.classList.contains('open')) {
            this.closeChat();
          } else {
            this.openChat();
          }
        }
      });
    }
    
    const chatCloseBtn = document.getElementById('chatCloseBtn');
    if (chatCloseBtn) {
      chatCloseBtn.addEventListener('click', () => {
        this.closeChat();
      });
    }
    
    // Chat Form Submission
    const chatForm = document.getElementById('chatForm');
    if (chatForm) {
      chatForm.addEventListener('submit', (e) => this.onChatSubmit(e));
    }
    
    // Listen for chat messages (expression changes on typing)
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
      chatInput.addEventListener('input', (e) => this.onChatInput(e));
    }
    
    // Listen for mood changes
    const moodInputs = document.querySelectorAll('input[name="mood"]');
    moodInputs.forEach(input => {
      input.addEventListener('change', (e) => this.onMoodChange(e.target.value));
    });
    
    // Listen for genre/language changes
    const genreSelect = document.getElementById('genreSelect');
    if (genreSelect) {
      genreSelect.addEventListener('change', (e) => this.recordPreference('genres', e.target.value));
    }
    
    const languageSelect = document.getElementById('languageSelect');
    if (languageSelect) {
      languageSelect.addEventListener('change', (e) => this.recordPreference('languages', e.target.value));
    }
  },
  
  // Detect language from text
  detectLanguage(text) {
    for (const [lang, pattern] of Object.entries(this.languagePatterns)) {
      if (pattern.test(text)) {
        return lang;
      }
    }
    return 'english'; // Default
  },
  
  // Detect emotion from text with enhanced analysis
  detectEmotion(text) {
    let detectedEmotion = null;
    let highestIntensity = 0;
    
    for (const [emotion, data] of Object.entries(this.emotionPatterns)) {
      if (data.patterns.test(text)) {
        const intensity = data.intensity === 'high' ? 3 : data.intensity === 'medium' ? 2 : 1;
        if (intensity > highestIntensity) {
          highestIntensity = intensity;
          detectedEmotion = emotion;
        }
      }
    }
    
    return detectedEmotion;
  },
  
  // Detect reasoning patterns for contextual understanding
  detectReasoning(text) {
    for (const [reason, pattern] of Object.entries(this.reasoningPatterns)) {
      if (pattern.test(text)) {
        return reason;
      }
    }
    return null;
  },
  
  // Get appropriate emoji based on emotion and context
  getContextualEmoji(emotion, context = 'general') {
    const emojiMap = {
      sad: ['😔', '💙', '🤗', '😢'],
      happy: ['😊', '🎉', '✨', '🌟'],
      excited: ['🤩', '🎉', '🚀', '⭐'],
      romantic: ['❤️', '💕', '🌹', '💖'],
      thrilling: ['😱', '🎬', '🔥', '⚡'],
      motivated: ['💪', '🚀', '✨', '🌟'],
      dark: ['🌑', '🎭', '🔮', '📚'],
      funny: ['😂', '🤣', '😄', '🎭'],
      stressed: ['😌', '🧘', '☕', '🌸'],
      curious: ['🤔', '🔍', '💡', '📖'],
      nostalgic: ['📷', '🎞️', '💭', '✨'],
      supportive: ['💙', '🤗', '❤️', '✨'],
      thinking: ['🤔', '💭', '🧠', '✨'],
      recommendation: ['🎬', '🍿', '✨', '🌟']
    };
    
    const emojis = emojiMap[emotion] || emojiMap[context] || ['😊'];
    return emojis[Math.floor(Math.random() * emojis.length)];
  },
  
  // Set animation state
  setState(state) {
    const fabContainer = document.getElementById('moumiFabContainer');
    const headerContainer = document.getElementById('moumiHeaderContainer');
    
    // Update FAB Moumi state
    if (fabContainer) {
      fabContainer.className = `moumi-container moumi-in-fab moumi-state-${state}`;
    }
    
    // Update header Moumi state
    if (headerContainer) {
      headerContainer.className = `moumi-container moumi-in-header moumi-state-${state}`;
    }
    
    this.currentState = state;
  },
  
  // Update Moumi visibility based on chat state
  updateMoumiVisibility(chatOpen) {
    const fabContainer = document.getElementById('moumiFabContainer');
    const headerContainer = document.getElementById('moumiHeaderContainer');
    const closeIcon = document.querySelector('.chat-fab-close-icon');
    const chatFab = document.getElementById('chatFab');
    
    if (chatOpen) {
      // Chat is open - FAB hidden, header visible
      if (fabContainer) {
        fabContainer.style.display = 'none';
      }
      if (headerContainer) {
        headerContainer.style.display = 'inline-block';
      }
      if (closeIcon) {
        closeIcon.style.display = 'block';
      }
      if (chatFab) {
        chatFab.classList.add('chat-open');
      }
    } else {
      // Chat is closed - FAB visible, header hidden
      if (fabContainer) {
        fabContainer.style.display = 'block';
      }
      if (headerContainer) {
        headerContainer.style.display = 'none';
      }
      if (closeIcon) {
        closeIcon.style.display = 'none';
      }
      if (chatFab) {
        chatFab.classList.remove('chat-open');
      }
    }
  },
  
  // Show speech bubble
  showSpeech(text, duration = 3000) {
    // Determine which Moumi instance is visible
    const fabCharacter = document.getElementById('moumiFabCharacter');
    const headerCharacter = document.getElementById('moumiHeaderCharacter');
    
    const character = fabCharacter || headerCharacter;
    if (!character) return;
    
    // Get SVG element (since it is inlined, it is the character itself!)
    const speechBubble = character.querySelector('.moumi-speech-bubble');
    const speechText = character.querySelector('.moumi-speech-text');
    
    if (speechBubble && speechText) {
      speechText.textContent = text;
      speechBubble.classList.add('visible');
      
      setTimeout(() => {
        speechBubble.classList.remove('visible');
      }, duration);
    }
  },
  
  // Show typing indicator (add to chat messages instead)
  showTyping(show = true) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;
    
    if (show) {
      // Add typing indicator to chat
      const typingDiv = document.createElement('div');
      typingDiv.className = 'chat-message chat-message-moumi typing-indicator';
      typingDiv.id = 'moumiTyping';
      typingDiv.innerHTML = `
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      `;
      chatMessages.appendChild(typingDiv);
      chatMessages.scrollTop = chatMessages.scrollHeight;
    } else {
      // Remove typing indicator
      const typingDiv = document.getElementById('moumiTyping');
      if (typingDiv) {
        typingDiv.remove();
      }
    }
  },
  
  // Open chatbot window
  openChat() {
    const win = document.getElementById('chatWindow');
    const fab = document.getElementById('chatFab');
    const input = document.getElementById('chatInput');
    
    if (win && fab) {
      win.classList.add('open');
      win.setAttribute('aria-hidden', 'false');
      fab.setAttribute('aria-expanded', 'true');
      this.updateMoumiVisibility(true);
      
      // If conversation history is empty, add welcome message
      const chatMessages = document.getElementById('chatMessages');
      if (chatMessages && chatMessages.children.length === 0) {
        const lang = this.detectLanguage(PAGE.userName || '');
        const welcomeMsg = this.getResponse(lang, 'welcome_new');
        this.addChatMessage(welcomeMsg, 'moumi');
      }
      
      if (input) input.focus();
    }
  },
  
  // Close chatbot window
  closeChat() {
    const win = document.getElementById('chatWindow');
    const fab = document.getElementById('chatFab');
    
    if (win && fab) {
      win.classList.remove('open');
      win.setAttribute('aria-hidden', 'true');
      fab.setAttribute('aria-expanded', 'false');
      this.updateMoumiVisibility(false);
    }
  },
  
  // On chat form submit
  async onChatSubmit(event) {
    event.preventDefault();
    const input = document.getElementById('chatInput');
    if (!input) return;
    
    const text = input.value.trim();
    if (!text) return;
    
    input.value = '';
    
    // Check safety
    const safetyWarning = this.checkSafety(text);
    if (safetyWarning) {
      this.addChatMessage(text, 'user');
      this.setState('supportive');
      this.addChatMessage(safetyWarning, 'moumi');
      setTimeout(() => this.setState('idle'), 3000);
      return;
    }
    
    this.addChatMessage(text, 'user');
    await this.sendChatbotMessage(text);
  },
  
  // Send message to chatbot endpoint
  async sendChatbotMessage(message) {
    this.setState('thinking');
    this.showTyping(true);
    
    const mood = document.querySelector('input[name="mood"]:checked')?.value || 'happy';
    const region = PAGE.region || '';
    
    try {
      const response = await fetch('/chatbot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          mood,
          region,
          client_time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          client_hour: new Date().getHours(),
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
        })
      });
      
      const data = await response.json();
      this.showTyping(false);
      
      if (data.reply) {
        // Detect response emotion to update face
        const detectedEmotion = this.detectEmotion(data.reply);
        const stateMap = {
          sad: 'supportive',
          happy: 'happy',
          excited: 'excited',
          romantic: 'happy',
          thrilling: 'excited',
          motivated: 'happy',
          dark: 'thinking',
          funny: 'happy',
          stressed: 'calm',
          curious: 'curious',
          nostalgic: 'nostalgic'
        };
        const state = stateMap[detectedEmotion] || 'happy';
        this.setState(state);
        
        // Add message
        this.addChatMessage(data.reply, 'moumi');
        
        setTimeout(() => {
          this.setState('idle');
        }, 3000);
      } else {
        this.addChatMessage("I'm not sure — try asking about a mood or genre! 🍿", 'moumi');
        this.setState('idle');
      }
    } catch (e) {
      console.error('Chatbot error:', e);
      this.showTyping(false);
      this.addChatMessage("Oops — I lost signal. Try again in a moment! 📡", 'moumi');
      this.setState('idle');
    }
  },
  
  // On Moumi click
  onMoumiClick() {
    this.openChat();
    this.setState('happy');
    const lang = this.detectLanguage(PAGE.userName || '');
    const response = this.getResponse(lang, 'greeting');
    
    this.addChatMessage(response, 'moumi');
    
    setTimeout(() => {
      this.setState('idle');
    }, 2000);
  },
  
  // On Moumi hover
  onMoumiHover() {
    this.setState('excited');
    
    setTimeout(() => {
      this.setState('idle');
    }, 500);
  },
  
  // On chat input (micro-animations only)
  onChatInput(event) {
    const text = event.target.value;
    if (text.length < 3) return;
    
    // Change expression as user types
    const emotion = this.detectEmotion(text);
    if (emotion) {
      const stateMap = {
        sad: 'supportive',
        happy: 'happy',
        excited: 'excited',
        romantic: 'happy',
        thrilling: 'excited',
        motivated: 'happy',
        dark: 'thinking',
        funny: 'happy',
        stressed: 'calm',
        curious: 'curious',
        nostalgic: 'nostalgic'
      };
      const state = stateMap[emotion] || 'happy';
      this.setState(state);
    } else {
      this.setState('idle');
    }
    
    const lang = this.detectLanguage(text);
    this.recordPreference('searches', text);
  },
  
  // On mood change
  onMoodChange(mood) {
    this.recordPreference('moodHistory', mood);
    
    const emotionMap = {
      happy: 'happy',
      sad: 'sad',
      excited: 'excited',
      romantic: 'romantic',
      thrilling: 'thrilling',
      motivated: 'motivated',
      dark: 'dark',
      funny: 'funny'
    };
    
    const emotion = emotionMap[mood] || 'happy';
    this.handleEmotion(emotion);
  },
  
  // Handle emotion with enhanced learning
  handleEmotion(emotion, text = '') {
    const reasoning = this.detectReasoning(text);
    
    // Learn from this interaction
    this.learnFromInteraction(text, emotion, reasoning);
    
    // Map emotion to Moumi state
    const stateMap = {
      sad: 'supportive',
      happy: 'happy',
      excited: 'excited',
      romantic: 'happy',
      thrilling: 'excited',
      motivated: 'happy',
      dark: 'thinking',
      funny: 'happy',
      stressed: 'calm',
      curious: 'curious',
      nostalgic: 'nostalgic',
      supportive: 'supportive',
      thinking: 'thinking',
      recommendation: 'recommendation'
    };
    
    const state = stateMap[emotion] || 'happy';
    this.setState(state);
    
    // Get personalized response based on learning
    const response = this.getPersonalizedResponse(emotion, reasoning);
    
    // Add message to chat with contextual emoji
    const emoji = this.getContextualEmoji(emotion);
    const enhancedResponse = `${response} ${emoji}`;
    this.addChatMessage(enhancedResponse, 'moumi');
    
    setTimeout(() => {
      this.setState('idle');
    }, 3000);
  },
  
  // Add chat message
  addChatMessage(text, sender = 'moumi') {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message chat-message-${sender}`;
    
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    if (sender === 'moumi') {
      messageDiv.innerHTML = `
        <div class="chat-message-avatar">
          <div class="moumi-container moumi-in-header moumi-state-${this.currentState}">
            <img src="/static/moumi.svg" alt="Moumi" class="moumi-character">
          </div>
        </div>
        <div class="chat-message-content">
          <div class="chat-message-text">${text}</div>
          <time class="chat-time">${time}</time>
        </div>
      `;
      // Inline the newly added avatar SVG too
      const img = messageDiv.querySelector('img.moumi-character');
      if (img) this.inlineAllMascotSVGs();
    } else {
      messageDiv.innerHTML = `
        <div class="chat-message-content">
          <div class="chat-message-text">${text}</div>
          <time class="chat-time">${time}</time>
        </div>
      `;
    }
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  },
  
  // Safety guidelines and AI assistant boundaries
  safetyGuidelines: {
    // Topics Moumi should not claim expertise in
    restrictedTopics: [
      'medical advice',
      'legal advice',
      'financial advice',
      'therapy',
      'mental health treatment',
      'diagnosis'
    ],
    
    // Responses for restricted topics
    restrictedResponses: {
      english: "I'm your AI movie companion, not a professional advisor. For medical, legal, or financial matters, please consult a qualified professional. However, I can suggest some comforting films if you'd like! 🎬",
      bengali: "আমি তোমার সিনেমা সঙ্গী, পেশাদার উপদেষ্টা নই। চিকিৎসা, আইনি বা আর্থিক বিষয়ের জন্য দয়া করে যোগ্য পেশাদারের সাথে পরামর্শ করুন। তবে আমি কিছু আরামদায়ক সিনেমা সাজেস্ট করতে পারি! 🎬",
      hindi: "मैं आपका AI फिल्म साथी हूं, पेशेवर सलाहकार नहीं। चिकित्सा, कानूनी या वित्तीय मामलों के लिए कृपया योग्य पेशेवर से परामर्श लें। हालांकि, मैं आपको कुछ आरामदायक फिल्में सुझा सकता हूं! 🎬",
      tamil: "நான் உங்கள் AI திரைப்பட தோழர், தொழில்முறை ஆலோசகர் அல்ல. மருத்துவ, சட்ட அல்லது நிதி விவகாரங்களுக்கு தயவு செய்து தகுதியான தொழில்முறை நிபுணரை அணுகுங்கள். இருப்பினும், நான் சில ஆறுதலான படங்களை பரிந்துரைக்கலாம்! 🎬"
    }
  },
  
  // Check if message contains restricted topic
  checkSafety(text) {
    const lang = this.detectLanguage(text);
    const lowerText = text.toLowerCase();
    
    for (const topic of this.safetyGuidelines.restrictedTopics) {
      if (lowerText.includes(topic)) {
        const response = this.safetyGuidelines.restrictedResponses[lang] || 
                        this.safetyGuidelines.restrictedResponses.english;
        return response;
      }
    }
    
    return null;
  },
  
  // Get response in language
  getResponse(language, key) {
    const lang = this.responses[language] || this.responses.english;
    let response = lang[key] || this.responses.english[key] || '';
    
    // Replace placeholders
    response = response.replace('{name}', PAGE.userName || 'Friend');
    
    return response;
  },
  
  // Enhanced memory and learning system
  conversationHistory: [],
  moodPatterns: [],
  interactionCount: 0,
  
  // Learn from user interaction
  learnFromInteraction(text, emotion, reasoning) {
    this.interactionCount++;
    
    // Store conversation history (last 20 messages)
    this.conversationHistory.push({
      text,
      emotion,
      reasoning,
      timestamp: Date.now()
    });
    
    if (this.conversationHistory.length > 20) {
      this.conversationHistory.shift();
    }
    
    // Track mood patterns (last 10 emotions)
    if (emotion) {
      this.moodPatterns.push({
        emotion,
        timestamp: Date.now()
      });
      
      if (this.moodPatterns.length > 10) {
        this.moodPatterns.shift();
      }
    }
    
    // Save to localStorage periodically
    if (this.interactionCount % 5 === 0) {
      this.saveConversationMemory();
    }
  },
  
  // Save conversation memory to localStorage
  saveConversationMemory() {
    try {
      const memory = {
        conversationHistory: this.conversationHistory,
        moodPatterns: this.moodPatterns,
        interactionCount: this.interactionCount
      };
      localStorage.setItem('moumi_conversation_memory', JSON.stringify(memory));
    } catch (e) {
      console.warn('Could not save conversation memory:', e);
    }
  },
  
  // Load conversation memory from localStorage
  loadConversationMemory() {
    try {
      const memory = localStorage.getItem('moumi_conversation_memory');
      if (memory) {
        const parsed = JSON.parse(memory);
        this.conversationHistory = parsed.conversationHistory || [];
        this.moodPatterns = parsed.moodPatterns || [];
        this.interactionCount = parsed.interactionCount || 0;
      }
    } catch (e) {
      console.warn('Could not load conversation memory:', e);
    }
  },
  
  // Get dominant mood from recent interactions
  getDominantMood() {
    if (this.moodPatterns.length === 0) return null;
    
    const moodCounts = {};
    this.moodPatterns.forEach(p => {
      moodCounts[p.emotion] = (moodCounts[p.emotion] || 0) + 1;
    });
    
    return Object.entries(moodCounts).sort((a, b) => b[1] - a[1])[0][0];
  },
  
  // Get personalized response based on learning
  getPersonalizedResponse(emotion, reasoning) {
    const dominantMood = this.getDominantMood();
    const lang = this.detectLanguage(PAGE.userName || '');
    
    // If user has a dominant mood pattern, acknowledge it
    if (dominantMood && dominantMood !== emotion && this.interactionCount > 5) {
      const moodMessages = {
        sad: {
          english: "I've noticed you've been feeling down lately. I'm here for you. 💙",
          bengali: "আমি লক্ষ্য করেছি তুমি সাম্প্রতিক সময়ে খারাপ বোধ করছ। আমি তোমার পাশে আছি। 💙",
          hindi: "मैंने देखा आप हाल ही में उदास रहे हैं। मैं आपके लिए हूं। 💙",
          tamil: "நான் கவனித்தேன் நீங்கள் சமீபத்தில் சோர்வாக இருந்தீர்கள். நான் உங்களுக்கு உள்ளேன்। 💙"
        },
        happy: {
          english: "I love seeing you in such good spirits! ✨",
          bengali: "তোমাকে এত ভালো মেজাজে দেখে আমি খুশি! ✨",
          hindi: "आपको इतने अच्छे मूड में देखकर अच्छा लगा! ✨",
          tamil: "உங்களை இவ்வளவு நல்ல மனநிலையில் பார்த்து மகிழ்ச்சி! ✨"
        },
        stressed: {
          english: "You seem stressed lately. Let me help you find some relaxing films. 😌",
          bengali: "তুমি সাম্প্রতিক সমযে চাপে আছো মনে হচ্ছে। কিছু শান্ত সিনেমা খুঁজে দিই। 😌",
          hindi: "आप हाल ही में तनाव में लगे हुए हैं। मैं आपको शांत फिल्में ढूंढने में मदद करूंगा। 😌",
          tamil: "நீங்கள் சமீபத்தில் மன அழுத்தத்தில் இருப்பதாகத் தெரிகிறது. சில அமைதியான படங்களைக் கண்டுபிடிக்க உதவுகிறேன்। 😌"
        }
      };
      
      const moodMsg = moodMessages[dominantMood];
      if (moodMsg && moodMsg[lang]) {
        return moodMsg[lang];
      }
    }
    
    // If reasoning pattern detected, use contextual response
    if (reasoning) {
      const reasoningKey = reasoning.replace(/([A-Z])/g, '_$1').toLowerCase();
      const response = this.getResponse(lang, reasoningKey);
      if (response) {
        return response;
      }
    }
    
    // Default to emotion-based response
    return this.getResponse(lang, emotion);
  },
  
  // Record user preference
  recordPreference(type, value) {
    if (!value || value === '' || value === 'All Languages') return;
    
    const prefs = this.userPreferences[type];
    if (Array.isArray(prefs)) {
      // Add if not already present (keep last 10)
      if (!prefs.includes(value)) {
        prefs.unshift(value);
        if (prefs.length > 10) prefs.pop();
      }
    }
    
    this.saveUserPreferences();
  },
  
  // Check if returning user
  checkReturningUser() {
    const lastVisit = localStorage.getItem('moumi_last_visit');
    const now = Date.now();
    
    if (lastVisit) {
      const daysSince = (now - parseInt(lastVisit)) / (1000 * 60 * 60 * 24);
      
      if (daysSince < 30) {
        // Returning user
        setTimeout(() => {
          this.showWelcomeBack();
        }, 2000);
      }
    }
    
    localStorage.setItem('moumi_last_visit', now.toString());
  },
  
  // Show welcome back message
  showWelcomeBack() {
    const fabContainer = document.getElementById('moumiFabContainer');
    if (fabContainer) {
      fabContainer.classList.add('welcome-animation');
    }
    
    this.setState('happy');
    
    const lang = this.detectLanguage(PAGE.userName || '');
    const response = this.getResponse(lang, 'welcome');
    
    // Add message to chat instead of speech bubble
    this.addChatMessage(response, 'moumi');
    
    // Add personalized touch based on preferences
    setTimeout(() => {
      this.addPersonalizedTouch();
    }, 3000);
    
    setTimeout(() => {
      this.setState('idle');
      if (fabContainer) {
        fabContainer.classList.remove('welcome-animation');
      }
    }, 6000);
  },
  
  // Add personalized touch based on user history
  addPersonalizedTouch() {
    const { genres, languages, moodHistory } = this.userPreferences;
    
    let message = '';
    
    if (genres.length > 0) {
      const topGenre = genres[0];
      const lang = this.detectLanguage(PAGE.userName || '');
      
      if (lang === 'bengali') {
        message = `আমি লক্ষ্য করেছি তুমি ${topGenre} পছন্দ করো। 🎬`;
      } else if (lang === 'hindi') {
        message = `मैंने देखा आपको ${topGenre} पसंद है। 🎬`;
      } else if (lang === 'tamil') {
        message = `நான் கவனித்தேன் நீங்கள் ${topGenre} விரும்புகிறீர்கள்। 🎬`;
      } else {
        message = `I noticed you enjoy ${topGenre} movies. 🎬`;
      }
      
      // Add message to chat instead of speech bubble
      this.addChatMessage(message, 'moumi');
    }
  },
  
  // Trigger recommendation state
  onRecommendation() {
    this.setState('recommendation');
    this.showTyping(true);
    
    setTimeout(() => {
      this.showTyping(false);
      const lang = this.detectLanguage(PAGE.userName || '');
      const response = this.getResponse(lang, 'recommendation');
      
      // Add message to chat instead of speech bubble
      this.addChatMessage(response, 'moumi');
      
      setTimeout(() => {
        this.setState('idle');
      }, 2000);
    }, 1500);
  },
  
  // Trigger thinking state
  onThinking() {
    this.setState('thinking');
    this.showTyping(true);
    
    setTimeout(() => {
      this.showTyping(false);
      this.setState('idle');
    }, 2000);
  }
};

// Initialize Moumi when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => MOUMI.init());
} else {
  MOUMI.init();
}

// Export for use in other scripts
window.MOUMI = MOUMI;
