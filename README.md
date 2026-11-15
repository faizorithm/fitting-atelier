# Fitting Atelier 👗
### A Digital Wardrobe & AI-Powered Fashion Recommendation Prototype

Fitting Atelier is a personal wardrobe management application built with Python, Flask, and SQLite. Originally developed as a database design project, it is being extended with natural language processing to explore personalized clothing recommendations.

## The Problem

Choosing what to wear can be time-consuming, especially when users have difficulty keeping track of the clothing they already own.

Fitting Atelier explores how structured wardrobe data and semantic similarity can help users discover relevant clothing items for different occasions.

## Features

**Flask Web Application**
- User registration and login
- Wardrobe inventory management
- Clothing organization by brand and category
- Outfit creation and management
- SQLite relational database

**AI Recommendation Prototype**
- Hugging Face SentenceTransformers
- Text embeddings using `all-MiniLM-L6-v2`
- Cosine similarity to compare user requests with clothing descriptions
- Ranking clothing items by semantic relevance

## Technologies

- **Backend:** Python, Flask
- **Database:** SQLite
- **Frontend:** HTML, CSS, Jinja2
- **AI/NLP:** Hugging Face SentenceTransformers
- **Development:** Google Colab, Jupyter Notebook, VS Code

## How the AI Works

1. A user describes what they need, such as "I need something professional for a job interview."
2. The SentenceTransformer model converts the request into a 384-dimensional embedding.
3. Clothing descriptions are converted into embeddings using the same model.
4. Cosine similarity measures the semantic similarity between the request and each clothing description.
5. The prototype recommends the highest-scoring item.

The AI demonstration currently uses sample clothing data. Integration with the Flask application's database is planned.

## Project Status

**In development:** The Flask wardrobe management application and standalone AI recommendation notebook are implemented. The AI integration and recommendation evaluation are future development goals.

## Future Improvements

- Connect AI recommendations to users' saved wardrobes.
- Improve clothing descriptions using categories, colors, and occasions.
- Evaluate recommendation quality using multiple test requests.
- Develop an interactive recommendation interface.

## Project Motivation

Fitting Atelier began as an exploration of relational database design and evolved into an opportunity to study how natural language processing can support more personalized, human-centered applications.
