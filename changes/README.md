# Changelog Way of Working

The changelog file in this project is maintained by [towncrier](https://github.com/twisted/towncrier).

New entries are added to this folder as different individual files to avoid conflicts when different features are worked on in parallel, and also when porting changes to different branches.

Notice you don't need it installed on you dev machine, as long as you create the fragment files in the correct format, the CI will take care of the rest.

Check out its documentation for more details: <https://towncrier.readthedocs.io/en/stable/tutorial.html#creating-news-fragments>
