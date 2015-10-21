---
layout: docs
title: Initial Blocks
short_title: Initial Blocks
---

## metadata

{% highlight yaml %}
---
metadata:
  description: |
    A divorce advice interview
  authors:
    - name: John Doe
      organization: Example, Inc.
  revision_date: 2015-09-28
---
{% endhighlight %}

A `metadata` block contains information about the YAML file, such as
the name of the author.  It must be a YAML dictionary, but each the
dictionary items can contain any arbitrary YAML structure.

## objects

{% highlight yaml %}
---
objects:
  - spouse: Individual
  - user.case: Case
---
{% endhighlight %}

An `objects` block creates objects that may be referenced in your
interview.  See [objects]({{ site.baseurl }}/docs/objects.md) for more
information about objects in **docassemble**.

If your interview references the variable `spouse`, **docassemble**
will find the above `objects` block and process it.  It will define
`spouse` as an instance of the object class `Individual` and define
`user.case` as an instance of the object class `Case`.

The use of objects in **docassemble** interviews is highly encouraged.
However, the objects you use as variables in your interview YAML files
need to inherit from the class `DAObject`.  Otherwise, **docassemble**
might not be able to find the appopriate code blocks or questions
necessary to define them.  This is because of the way **docassemble**
keeps track of the names of variables.

A code block like this would effectively do the same thing as the
`objects` block above:

{% highlight yaml %}
---
code: |
  spouse = Individual('spouse')
  user.initializeAttribue(name='case', objectType=Case)
---
{% endhighlight %}

This code is more complicated than normal Python code for object
initialization because the full name of the variable needs to be
supplied to the function that creates and initializes the object.  The
base class `DAObject` keeps track of variable names.

Whenever possible, you should use `objects` blocks rather than code to
initialize your objects.  `objects` blocks are clean and readable.

## include

{% highlight yaml %}
---
include:
  - basic-questions.yml
  - docassemble.helloworld:questions.yml
---
{% endhighlight %}

The `include` statement incorporates the questions in another YAML
file, almost as if the contents of the other YAML file appeared in
place of the `include` statement.  When the `include`d file is parsed,
files referenced within it will be assumed to be located in the
`include`d file's package.

When a filename is provided without a package name, **docassemble**
will look first in the `data/questions` directory of the current
package (i.e., the package within which the YAML file being read is
located), and then in the `data/questions` directory of
`docassemble.base`.

You can include question files from other packages by explicitly
referring to their package names.  E.g.,
`docassemble.helloworld:questions.yml` refers to the file
`questions.yml` in the `docassemble/helloworld/data/questions`
directory of that package.

## image sets

{% highlight yaml %}
---
image sets:
  freepik:
    attribution: |
      Icon made by [Freepik](http://www.flaticon.com/authors/freepik)
    images:
      baby: crawling.svg
      people: users6.svg
      injury: accident3.svg
---
{% endhighlight %}

An `image sets` block defines the names of icons that you can use to
decorate your questions.

The file names refer to files located in the `data/static` directory
of the package in which the YAML file is located.

Since most free icons available on the internet require attribution,
the `image sets` block allows you to specify what attribution text
to use for particular icons.  The web app shows the appropriate
attribution text at the bottom of any page that uses one of the
icons.  The example above is for a collection of icons obtained from
the web site Freepik, which offers free icons under an
attribution-only license.

The `image sets` block must be in the form of a YAML dictionary, where
the names are the names of collections of icons.  The collection
itself is also a dictionary containing terms `images` and (optionally)
an `attribution`.  The `images` collection is a dictionary that
assigns names to icon files, so that you can refer to icons by a name
of your choosing rather than by the name of the image file.

For information on how to use the icons you have defined in an `image
sets` block, see `decoration` and `buttons`.

## images

{% highlight yaml %}
---
images:
  bills: money146.svg
  children: children2.svg
---
{% endhighlight %}

An `images` block is just like an `image sets` block, except that it
does not set any attribution information.  It is simpler because you
do not need to give a name to a "set" of images.

The above `images` block is essentially equivalent to writing:

{% highlight yaml %}
---
image sets:
  unspecified:
	images:
	  bills: money146.svg
	  children: children2.svg
---
{% endhighlight %}

## imports

{% highlight yaml %}
---
imports:
  - datetime
  - us
---
{% endhighlight %}

`imports` loads a Python module name into the namespace in which your
templates are evaluated.  The example above is equivalent to running
the following Python code:

{% highlight python %}
import datetime
import us
{% endhighlight %}

## modules

{% highlight yaml %}
---
modules:
  - datetime
---
{% endhighlight %}

Like `imports`, `modules` loads Python modules into the namespace in
which your templates are evaluated, except that it imports all of the
names that the module exports.  The example above is equivalent to
running the following Python code:

{% highlight python %}
from datetime import *
{% endhighlight %}

## terms

{% highlight yaml %}
---
terms:
  enderman: |
    A slender fellow from The End who carries enderpearls and picks up
	blocks.
  fusilli: |
	A pasta shape that looks like a corkscrew.
---
{% endhighlight %}

Sometimes you will use vocabulary that the user may or may not know.
Instead of interrupting the flow of your questions to define every
term, you can define certain vocabulary words, and **docassemble**
will turn them into hyperlinks wherever they appear.  When the user
clicks on the hyperlink, a popup appears with the word's definition.

## interview help

{% highlight yaml %}
---
interview help:
  heading: How to use this web site
  content: |
    Answer each question.  At the end, you will get a prize.
---
{% endhighlight %}

An `interview help` block adds text to the "Help" page of every
question in the interview.  If the question has `help` text of its
own, the `interview help` will appear after the question-specific
help.

## def

{% highlight yaml %}
def: adorability
mako: |
  <%def name="describe_as_adorable(person)"> \
  ${ person } is adorable. \
  </%def>
{% endhighlight %}

A `def` block allows you to define [Mako]
"[def](http://docs.makotemplates.org/en/latest/defs.html)" functions
that you can re-use later in your question or document templates.  You
can use the above function by doing:

{% highlight yaml %}
---
question: |
  ${ describe_as_adorable(spouse) } Am I right?
yesno: user_agrees_spouse_is_adorable
usedef:
 - adorability
---
{% endhighlight %}

Due to the way **docassemble** parses interviews, the `def` block
needs to be defined before it is used.

## default role

{% highlight yaml %}
---
default role: client
code: |
  if current_info['user']['is_authenticated'] and 'advocate' in current_info['user']['roles']:
    user = advocate
    role = 'advocate'
  else:
    user = client
    role = 'client'
  update_info(user, role, current_info)
---
{% endhighlight %}

If your interview uses the [roles]({{ site.baseurl}}/docs/roles.html)
feature for multi-user interviews, the `default role` statement will
define what role or roles will be required for any question that does
not contain an explicit `role` statement.

When you use the roles feature, you need to have some way of telling
your interview logic what the role of the interviewee is.

If you include `code` within the same block as your `default role`
statement, that code will be executed every time the interview logic
is processed, as if it was marked as `initial`.  For this reason, any
`default role` statement that contains code should be placed earlier
in the interview file than and `mandatory` questions or code blocks.

In the example above, the interview has two roles: "client" and
"advocate".  The special variables `user` and `role` are set in the
`code` block, which is executed every time the interview logic is
processed.

In addition, the `update_info()` function from
`docassemble.base.legal` is called.  This lets the linguistic
functions in `docassemble.base.legal` know who the user is, so that
questions can ask "What is your date of birth?" or "What is John
Smith's date of birth" depending on whether the current user is John
Smith or not.