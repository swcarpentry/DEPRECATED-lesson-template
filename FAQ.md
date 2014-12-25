## FAQ

*   *Where can I get help?*

    Mail [admin@software-carpentry.org](mailto:admin@software-carpentry.org),
    or join our [discussion list](http://lists.software-carpentry.org/mailman/listinfo/discuss_lists.software-carpentry.org)
    and ask for help there.

*   *Where can I report problems or suggest improvements?*

    Please
    [file an issue](https://github.com/swcarpentry/lesson-template/issues?q=is%3Aopen+is%3Aissue)
    or [mail us](mailto:admin@software-carpentry.org).

*   *Why does the lesson repository have to be created from scratch? Why not fork `lesson-template` on GitHub?*

    Because any particular user can only have one fork of a repository,
    but instructors frequently need to work on several workshops at once.

*   *Why use Pandoc?  Why not some other markup language and some other converter?*

    Because it supports a richer dialect of Markdown than Jekyll
    (the converter that GitHub uses by default).
    In particular, Pandoc can do tables and allows us to add styles to headings.

*   *What do the [labels](https://github.com/swcarpentry/lesson-template/issues?q=is%3Aopen+is%3Aissue) mean?*

    *   `bug`: something is wrong in our tools or documentation
    *   `defer`: marks an issue that we will work on, but not now
    *   `discussion`: marks issues used for conversations about specific problems and questions
    *   `duplicate`: marks an issue that was closed as redundant (include the number of the original issue in the closing comment)
    *   `enhancement`: asks for, or adds, a new feature or new information
    *   `filed-by-newcomer`: issue or pull request was filed by someone who is relatively new to GitHub and/or this project, and would appreciate guidance as well as feedback
    *   `getting-started`: issue or pull request is suitable for someone new to GitHub and/or this project
    *   `help-wanted`: a question or request for assistance
    *   `left-as-was`: marks an issue closed because the item in question will be left as it was
    *   `suitable-for-newcomer`: issue or pull request is a good starting point for someone who is relatively new to GitHub and/or this project
    *   `work-in-progress`: a pull request that is not yet ready for review

## Debugging

Please add notes about problems and solutions below.

*   `pandoc: command not found`

    Probably you didn't install [Pandoc](http://pandoc.org/installing.html).

*   `pandoc: Error running filter tools/filters/blockquote2div.py`
    due `ImportError: No module named 'pandocfilters'`

    Probably you didn't install
    [pandocfilters](https://pypi.python.org/pypi/pandocfilters/1.2.3).
