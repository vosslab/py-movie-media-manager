"""Offline regression checks for movie identity, metadata, and parental-guide parsing."""

import json

import moviemanager.scraper.imdb_parental_guide_scraper
import moviemanager.scraper.imdb_scraper


SAMPLE_SUGGESTION_RESPONSE = {
	"d": [
		{
			"id": "tt0109445",
			"l": "Clerks",
			"qid": "movie",
			"rank": 2345,
			"y": 1994,
			"i": {
				"imageUrl": "https://m.media-amazon.com/images/M/abc._V1_UX300_.jpg",
				"width": 300,
				"height": 450,
			},
		},
		{
			"id": "tt0305056",
			"l": "Clerks II",
			"qid": "movie",
			"rank": 5678,
			"y": 2006,
			"i": {
				"imageUrl": "https://m.media-amazon.com/images/M/def._V1_.jpg",
				"width": 300,
				"height": 450,
			},
		},
		{
			"id": "tt12629970",
			"l": "Clerks (1994)",
			"qid": "tvEpisode",
			"rank": 99999,
			"y": 2018,
		},
		{
			"id": "nm0003620",
			"l": "Kevin Smith",
			"qid": "",
			"rank": 1000,
		},
	],
	"q": "clerks",
	"v": 1,
}


SAMPLE_NEXT_DATA_TITLE = {
	"props": {
		"pageProps": {
			"aboveTheFoldData": {
				"titleText": {"text": "Clerks"},
				"originalTitleText": {"text": "Clerks"},
				"releaseYear": {"year": 1994},
				"releaseDate": {"day": 9, "month": 11, "year": 1994},
				"ratingsSummary": {
					"aggregateRating": 7.7,
					"voteCount": 239766,
					"topRanking": {"rank": 920},
				},
				"plot": {
					"plotText": {
						"plainText": "A day in the lives of two convenience clerks."
					}
				},
				"runtime": {"seconds": 5520},
				"certificate": {"rating": "R"},
				"genres": {"genres": [{"text": "Comedy"}]},
				"primaryImage": {
					"url": "https://m.media-amazon.com/images/M/abc._V1_UX300_.jpg"
				},
				"taglines": {
					"edges": [{"node": {"text": "Just because they serve you..."}}]
				},
				"countriesOfOrigin": {
					"countries": [{"id": "US", "text": "United States"}]
				},
				"spokenLanguages": {
					"spokenLanguages": [{"id": "en", "text": "English"}]
				},
				"companyCredits": {
					"edges": [
						{
							"node": {
								"company": {"companyText": {"text": "View Askew Productions"}},
								"category": {"text": "Production Companies"},
							}
						},
						{
							"node": {
								"company": {"companyText": {"text": "Miramax"}},
								"category": {"text": "Distributors"},
							}
						},
					]
				},
				"principalCredits": [
					{
						"category": {"text": "Director"},
						"credits": [
							{
								"name": {
									"id": "nm0003620",
									"nameText": {"text": "Kevin Smith"},
									"primaryImage": {"url": "https://example.com/smith._V1_.jpg"},
								}
							}
						],
					},
					{
						"category": {"text": "Writer"},
						"credits": [
							{
								"name": {
									"id": "nm0003620",
									"nameText": {"text": "Kevin Smith"},
									"primaryImage": None,
								}
							}
						],
					},
					{
						"category": {"text": "Stars"},
						"credits": [
							{
								"name": {
									"id": "nm0004778",
									"nameText": {"text": "Brian O'Halloran"},
									"primaryImage": {"url": "https://example.com/brian._V1_.jpg"},
								},
								"characters": [{"name": "Dante Hicks"}],
							},
							{
								"name": {
									"id": "nm0000492",
									"nameText": {"text": "Jeff Anderson"},
									"primaryImage": None,
								},
								"characters": [{"name": "Randal Graves"}],
							},
						],
					},
					{
						"category": {"text": "Producers"},
						"credits": [
							{
								"name": {
									"id": "nm0588201",
									"nameText": {"text": "Scott Mosier"},
									"primaryImage": None,
								}
							}
						],
					},
				],
				"parentsGuide": {
					"categories": [
						{"category": {"text": "Sex & Nudity"}, "severity": {"text": "Moderate"}},
						{"category": {"text": "Violence & Gore"}, "severity": {"text": "Mild"}},
						{"category": {"text": "Profanity"}, "severity": {"text": "Severe"}},
						{"category": {"text": "Alcohol, Drugs & Smoking"}, "severity": {"text": "Moderate"}},
						{"category": {"text": "Frightening & Intense Scenes"}, "severity": {"text": "Mild"}},
					]
				},
			},
			"mainColumnData": {
				"cast": {
					"edges": [
						{
							"node": {
								"name": {"id": "nm0004778"},
								"characters": [{"name": "Dante Hicks"}],
							}
						},
						{
							"node": {
								"name": {"id": "nm0000492"},
								"characters": [{"name": "Randal Graves"}],
							}
						},
					]
				},
				"keywords": {
					"edges": [
						{"node": {"text": "convenience store"}},
						{"node": {"text": "slacker"}},
					]
				},
			},
		}
	}
}


SAMPLE_NEXT_DATA_PARENTAL_GUIDE = {
	"props": {
		"pageProps": {
			"contentData": {
				"section": {
					"items": [
						{
							"id": "advisory-nudity",
							"severityVote": {"severity": "Moderate"},
						},
						{
							"id": "advisory-violence",
							"severityVote": {"severity": "Mild"},
						},
						{
							"id": "advisory-profanity",
							"severityVote": {"severity": "Severe"},
						},
						{
							"id": "advisory-alcohol",
							"severityVote": {"severity": "Moderate"},
						},
						{
							"id": "advisory-frightening",
							"severityVote": {"severity": "Mild"},
						},
					]
				}
			}
		}
	}
}


def _make_title_html(next_data: dict) -> str:
	"""Build a minimal IMDB page HTML with __NEXT_DATA__ script tag.

	Args:
		next_data: Dict to serialize as __NEXT_DATA__ JSON.

	Returns:
		str: HTML string with embedded __NEXT_DATA__.
	"""
	json_str = json.dumps(next_data)
	html = (
		"<html><head>"
		'<script id="__NEXT_DATA__" type="application/json">'
		+ json_str
		+ "</script>"
		"</head><body></body></html>"
	)
	return html


def test_parse_suggestion_results_filters_movies() -> None:
	"""Suggestion parser filters to movie types, excludes TV episodes and people."""
	entries = SAMPLE_SUGGESTION_RESPONSE["d"]
	results = moviemanager.scraper.imdb_scraper._parse_suggestion_results(entries)
	# only the two movies, not the TV episode or person
	assert len(results) == 2
	assert results[0].title == "Clerks"
	assert results[0].imdb_id == "tt0109445"
	assert results[0].year == "1994"
	assert results[1].title == "Clerks II"
	assert results[1].imdb_id == "tt0305056"
	assert results[1].year == "2006"


def test_parse_metadata_all_fields() -> None:
	"""Full metadata parsing populates all expected fields."""
	html = _make_title_html(SAMPLE_NEXT_DATA_TITLE)
	metadata = moviemanager.scraper.imdb_scraper._parse_metadata_html(
		html, "tt0109445"
	)
	assert metadata.title == "Clerks"
	assert metadata.original_title == "Clerks"
	assert metadata.year == "1994"
	assert metadata.release_date == "1994-11-09"
	assert metadata.rating == 7.7
	assert metadata.votes == 239766
	assert metadata.runtime == 92
	assert metadata.certification == "R"
	assert metadata.genres == ["Comedy"]
	assert metadata.director == "Kevin Smith"
	assert metadata.writer == "Kevin Smith"
	assert metadata.studio == "View Askew Productions"
	assert metadata.country == "United States"
	assert metadata.spoken_languages == "English"
	assert metadata.imdb_id == "tt0109445"
	assert metadata.media_source == "imdb"
	# poster URL should have resize params stripped
	assert metadata.poster_url.endswith("._V1_.jpg")
	assert "UX300" not in metadata.poster_url
	# tagline
	assert "Just because" in metadata.tagline
	# tags/keywords
	assert "convenience store" in metadata.tags
	assert "slacker" in metadata.tags
	# parental guide
	assert len(metadata.parental_guide) == 5
	assert metadata.parental_guide["Profanity"] == "Severe"
	# actors
	assert len(metadata.actors) == 2
	assert metadata.actors[0].name == "Brian O'Halloran"
	assert metadata.actors[0].role == "Dante Hicks"
	assert metadata.actors[0].department == "Acting"
	# producers
	assert len(metadata.producers) == 1
	assert metadata.producers[0].name == "Scott Mosier"


def test_parse_parental_guide_html() -> None:
	"""Parental guide categories are extracted from HTML page."""
	html = _make_title_html(SAMPLE_NEXT_DATA_PARENTAL_GUIDE)
	result = moviemanager.scraper.imdb_parental_guide_scraper._parse_parental_guide_html(html)
	assert "Sex & Nudity" in result
	assert result["Sex & Nudity"] == "Moderate"
	assert "Profanity" in result
	assert result["Profanity"] == "Severe"
	assert len(result) == 5


def test_parse_parental_guide_fallback_above_fold() -> None:
	"""Parental guide falls back to aboveTheFoldData format."""
	# use the title page format which has guide in aboveTheFoldData
	html = _make_title_html(SAMPLE_NEXT_DATA_TITLE)
	# the parental guide parser should find data in fallback path
	result = moviemanager.scraper.imdb_parental_guide_scraper._parse_parental_guide_html(html)
	# should find data from the aboveTheFoldData fallback
	assert len(result) == 5
	assert result["Profanity"] == "Severe"
