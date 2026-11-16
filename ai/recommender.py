
from itertools import product
from sentence_transformers import SentenceTransformer, util


# ==========================================
# HUGGING FACE MODEL
# ==========================================

model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2"
)


# ==========================================
# CLOTHING RECOMMENDATION
# ==========================================

def recommend_clothing(user_request, clothing_items):
    if not clothing_items:
        return []

    descriptions = []

    for item in clothing_items:
        description = (
            f"{item['clothing_item_color'] or ''} "
            f"{item['clothing_item_name']} "
            f"{item['category_name']} "
            f"{item['brand_name']}"
        )
        descriptions.append(description)

    request_embedding = model.encode(user_request)
    clothing_embeddings = model.encode(descriptions)

    similarity_scores = util.cos_sim(
        request_embedding,
        clothing_embeddings
    )[0]

    recommendations = []

    for item, score in zip(clothing_items, similarity_scores):
        recommendations.append({
            "item": dict(item),
            "score": float(score.item())
        })

    recommendations.sort(
        key=lambda result: result["score"],
        reverse=True
    )

    return recommendations


# ==========================================
# OCCASION DETECTION
# ==========================================

def detect_occasion(user_request):
    request = user_request.lower()

    # Specific occasions first
    if any(word in request for word in [
        "interview", "professional", "office",
        "business", "formal", "meeting"
    ]):
        return "formal"

    if any(word in request for word in [
        "workout", "gym", "running", "exercise"
    ]):
        return "athletic"

    if any(word in request for word in [
        "date", "dinner", "brunch"
    ]):
        if any(word in request for word in [
            "fancy", "elegant", "dressy", "formal"
        ]):
            return "formal"
        return "casual_date"

    return "casual"


# ==========================================
# STYLE COMPATIBILITY
# ==========================================

STYLE_KEYWORDS = {
    "formal": {
        "positive": [
            "blazer", "dress pants", "trousers",
            "button-down", "button down",
            "dress shirt", "loafers", "heels",
            "flats", "formal", "tailored"
        ],
        "negative": [
            "sneakers", "dunks", "hoodie",
            "graphic tee", "sweatpants",
            "running shoes"
        ]
    },

    "casual_date": {
        "positive": [
            "top", "blouse", "jeans", "skirt",
            "flats", "cardigan", "dress",
            "casual", "sneakers"
        ],
        "negative": [
            "dress pants", "business suit",
            "formal blazer", "gym",
            "running shoes", "sweatpants"
        ]
    },

    "casual": {
        "positive": [
            "t-shirt", "tee", "jeans",
            "sneakers", "dunks", "hoodie",
            "casual", "cardigan"
        ],
        "negative": [
            "business suit", "formal",
            "dress pants"
        ]
    },

    "athletic": {
        "positive": [
            "leggings", "sneakers", "running",
            "athletic", "sports", "gym",
            "t-shirt", "joggers"
        ],
        "negative": [
            "blazer", "dress pants",
            "heels", "loafers"
        ]
    }
}


def occasion_score(item, occasion):
    name = item["clothing_item_name"].lower()
    category = item["category_name"].lower()
    description = f"{name} {category}"

    rules = STYLE_KEYWORDS[occasion]

    score = 0.5

    for keyword in rules["positive"]:
        if keyword in description:
            score += 0.25

    for keyword in rules["negative"]:
        if keyword in description:
            score -= 0.35

    return max(0.0, min(1.0, score))


# ==========================================
# COLOR COORDINATION
# ==========================================

NEUTRAL_COLORS = {
    "black", "white", "cream", "beige",
    "gray", "grey", "brown", "navy"
}


def color_score(outfit):
    colors = []

    for result in outfit:
        color = (
            result["item"].get("clothing_item_color") or ""
        ).strip().lower()

        if color:
            colors.append(color)

    if len(colors) < 2:
        return 0.5

    neutral_count = sum(
        color in NEUTRAL_COLORS
        for color in colors
    )

    # Matching colors
    if len(set(colors)) == 1:
        return 1.0

    # Neutral colors with one accent color
    if neutral_count >= len(colors) - 1:
        return 0.9

    # Repeated accent color
    if len(set(colors)) < len(colors):
        return 0.85

    return 0.5


# ==========================================
# COMPLETE OUTFIT SCORING
# ==========================================

def calculate_outfit_score(outfit, occasion):
    # Normalize cosine similarities from [-1, 1] to [0, 1]
    semantic = sum(
        (result["score"] + 1) / 2
        for result in outfit
    ) / len(outfit)

    occasion_match = sum(
        occasion_score(result["item"], occasion)
        for result in outfit
    ) / len(outfit)

    colors = color_score(outfit)

    total = (
        0.40 * semantic +
        0.35 * occasion_match +
        0.25 * colors
    )

    return total


# ==========================================
# BUILD COMPLETE OUTFIT
# ==========================================

def recommend_outfit(user_request, clothing_items):
    if not clothing_items:
        return {
            "outfit": [],
            "missing": ["Tops", "Bottoms", "Shoes"],
            "explanation": ""
        }

    occasion = detect_occasion(user_request)

    ranked_items = recommend_clothing(
        user_request,
        clothing_items
    )

    grouped = {}

    for result in ranked_items:
        category = result["item"]["category_name"]
        grouped.setdefault(category, []).append(result)

    # Support dresses as an alternative to top + bottom
    combinations = []

    tops = grouped.get("Tops", [])
    bottoms = grouped.get("Bottoms", [])
    shoes = grouped.get("Shoes", [])
    dresses = grouped.get("Dress", [])

    # Top + bottom + shoes combinations
    if tops and bottoms and shoes:
        for top, bottom, shoe in product(
            tops[:10], bottoms[:10], shoes[:10]
        ):
            combinations.append([top, bottom, shoe])

    # Dress + shoes combinations
    if dresses and shoes:
        for dress, shoe in product(
            dresses[:10], shoes[:10]
        ):
            combinations.append([dress, shoe])

    # If the wardrobe is incomplete, use available categories
    if not combinations:
        fallback = []

        for category in ["Tops", "Bottoms", "Shoes"]:
            if grouped.get(category):
                fallback.append(grouped[category][0])

        if not fallback and dresses:
            fallback = [dresses[0]]

        combinations = [fallback] if fallback else []

    if not combinations:
        return {
            "outfit": [],
            "missing": ["Tops", "Bottoms", "Shoes"],
            "explanation": "No suitable clothing combinations found."
        }

    best_outfit = max(
        combinations,
        key=lambda outfit: calculate_outfit_score(
            outfit, occasion
        )
    )

    # Optional outerwear for formal occasions
    if occasion == "formal" and grouped.get("Outerwear"):
        outerwear = max(
            grouped["Outerwear"],
            key=lambda result: (
                0.5 * occasion_score(result["item"], occasion)
                + 0.5 * ((result["score"] + 1) / 2)
            )
        )
        best_outfit.append(outerwear)

    selected_categories = {
        result["item"]["category_name"]
        for result in best_outfit
    }

    if "Dress" in selected_categories:
        required = ["Dress", "Shoes"]
    else:
        required = ["Tops", "Bottoms", "Shoes"]

    missing = [
        category for category in required
        if category not in selected_categories
    ]

    # Explain the outfit based on the rules actually used
    selected_names = [
        result["item"]["clothing_item_name"]
        for result in best_outfit
    ]

    explanation = (
        f"For your {occasion.replace('_', ' ')} request, "
        f"Fitting Atelier selected "
        f"{', '.join(selected_names)}. "
        "The combination was chosen by comparing semantic "
        "similarity, occasion compatibility, and color "
        "coordination across available wardrobe items. "
        "These are heuristic scores, not guarantees "
        "of fashion suitability."
    )

    return {
        "outfit": best_outfit,
        "missing": missing,
        "explanation": explanation
    }
