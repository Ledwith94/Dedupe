# Forensic Disc Image Reconstruction From Deduplicated Data Storeage

This project was completed as part of my final year project in completion of my undergraduate degree in computer science.
It was designed to remotely acquire the entirety of a suspects device and transfer it to a remote server.

However, this project was designed to use a deduplicated data store. This means that each file was checked against a database of previously acquired files. If a file was already found on the server, only the metadata would be uploaded. 

After the disc was fully acquired the image would be recreated, server-side, from the files that had either been previously uploaded or had just been acquired from the image in question.

Both the new and original image would be hashed and checked if they were identical. If both were the same then the recreated image could be deemed forensically sound.
