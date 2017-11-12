The contents of this folder are copied to the lookout s3 bucket with `make testdata`

`make index` will run the LookoutIndexFaces lambda which will index each .jpg in this folder as a face.  

Each jpg should contain one face.  The filename will be used as the name of the person.  For example, a file named `Bob.jpg` will attach the name "Bob" to the face and will be used to announce the name via the notifier.

If you wish to index multiple images for the same person (more images will help lookout get positive matches) the files can be named this way:

```
Bob_1.jpg
Bob_2.jpg
Bob_3.jpg
```

All 3 images will be indexed with the name "Bob" attached.
