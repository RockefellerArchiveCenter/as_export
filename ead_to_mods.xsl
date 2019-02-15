<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns="http://www.loc.gov/mods/v3"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:ead="urn:isbn:1-931666-22-9"
    xmlns:xs="http://www.w3.org/2001/XMLSchema" exclude-result-prefixes="xs ead"
    xmlns:xd="http://www.oxygenxml.com/ns/doc/xsl"
    xmlns:str="http://exslt.org/strings" extension-element-prefixes="str" version="1.0">
    <!--
    Transforms ArchivesSpace EAD to valid MODS 3.4 records for import into XTF.
    This stylesheet uses XSLT 1.0 since lxml cannot handle XSLT 2.0. Sad face.
    Modified from a stylesheet created by Winona Salesky wsalesky@gmail.com for transforming Archivists ToolKit ead.xml
    -->

    <xsl:template match="/">
        <!-- <xsl:result-document href="{concat($fileName,'/',$newFile)}"> -->
            <mods xsi:schemaLocation="http://www.loc.gov/mods/v3 http://www.loc.gov/standards/mods/v3/mods-3-4.xsd"
                version="3.4" xmlns="http://www.loc.gov/mods/v3" xmlns:xlink="http://www.w3.org/1999/xlink"
                xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
                <xsl:apply-templates select="/ead:ead/ead:archdesc/ead:did/ead:unitid"/>
                <xsl:apply-templates select="/ead:ead/ead:archdesc/ead:did/ead:unittitle"/>
                <xsl:apply-templates select="/ead:ead/ead:archdesc/ead:odd[ead:head='Uniform Title']"/>
                <xsl:apply-templates select="/ead:ead/ead:archdesc/ead:odd[ead:head='Variant Title']"/>
                <xsl:apply-templates select="/ead:ead/ead:archdesc/ead:did/ead:origination[child::*[not(starts-with(@label,'pub'))]]"/>
                <xsl:call-template name="publicationInfo"/>
                <xsl:call-template name="physicalDesc"/>
                <xsl:call-template name="series"/>
                <xsl:apply-templates select="/ead:ead/ead:archdesc/ead:odd[starts-with(ead:head,'General note')]"/>
                <xsl:apply-templates select="/ead:ead/ead:archdesc/ead:scopecontent"/>
                <xsl:apply-templates select="/ead:ead/ead:archdesc/ead:controlaccess"/>
                <xsl:apply-templates select="/ead:ead/ead:archdesc/ead:acqinfo[starts-with(ead:head,'Immediate Source of Acquisition')]"/>
                <xsl:apply-templates select="/ead:ead/ead:archdesc/ead:relatedmaterial"/>
                <xsl:apply-templates select="/ead:ead/ead:archdesc/ead:originalsloc"/>
                <xsl:apply-templates select="/ead:ead/ead:archdesc/ead:altformavail"/>
                <xsl:apply-templates select="/ead:ead/ead:archdesc/ead:fileplan[starts-with(ead:head,'ISBN')]"/>
                <xsl:apply-templates select="/ead:ead/ead:archdesc/ead:fileplan[starts-with(ead:head,'ISSN')]"/>
                <xsl:apply-templates select="/ead:ead/ead:archdesc/ead:fileplan[starts-with(ead:head,'OCLC')]"/>
                <xsl:apply-templates select="/ead:ead/ead:archdesc/ead:fileplan[starts-with(ead:head,'LC')]"/>
                <xsl:apply-templates select="/ead:ead/ead:archdesc/ead:did/ead:container"/>
            </mods>
        <!-- </xsl:result-document> -->
    </xsl:template>

    <!-- Prevents unmapped fields from exporting to MODS -->
    <xsl:template match="*"/>

    <!-- Resource ID -->
    <xsl:template match="/ead:ead/ead:archdesc/ead:did/ead:unitid">
        <identifier type="local"><xsl:value-of select="."/></identifier>
    </xsl:template>

    <!-- Title -->
    <xsl:template match="/ead:ead/ead:archdesc/ead:did/ead:unittitle">
        <titleInfo>
            <title><xsl:apply-templates/></title>
        </titleInfo>
    </xsl:template>
    <!-- Alternative Titles -->
    <xsl:template match="/ead:ead/ead:archdesc/ead:odd[ead:head='Uniform Title']">
        <titleInfo type="uniform">
            <title><xsl:value-of select="ead:p"/></title>
        </titleInfo>
    </xsl:template>
    <xsl:template match="/ead:ead/ead:archdesc/ead:odd[ead:head='Variant Title']">
        <titleInfo type="alternative">
            <title><xsl:value-of select="ead:p"/></title>
        </titleInfo>
    </xsl:template>

    <!-- Creator -->
    <!-- NOTE: may want to parse out nameparts, at least the date -->
    <xsl:template match="/ead:ead/ead:archdesc/ead:did/ead:origination[child::*[not(starts-with(@role,'pub'))]]">
        <xsl:variable name="name" select="normalize-space(child::*)"/>
        <name>
            <namePart>
                <xsl:choose>
                    <xsl:when test="', ' = substring(., string-length(.) - string-length(', ') +1)">
                        <xsl:variable name="sl" select="string-length(.)-2"/>
                        <xsl:value-of select="substring(.,1,$sl)"/>
                    </xsl:when>
                    <xsl:otherwise>
                        <xsl:value-of select="."/>
                    </xsl:otherwise>
                </xsl:choose>
            </namePart>
            <xsl:if test="child::*/@role !=''">
                <role>
                    <roleTerm type="text" authority="{child::*/@source}"><xsl:value-of select="child::*/@role"/></roleTerm>
                </role>
            </xsl:if>
        </name>
    </xsl:template>

    <!-- Publication Information -->
    <xsl:template name="publicationInfo">
        <xsl:if test="/ead:ead/ead:archdesc/ead:bibliography[starts-with(head,'Publication')]
            or /ead:ead/ead:archdesc/ead:odd[starts-with(ead:head,'Edition Statement')]
            or /ead:ead/ead:archdesc/ead:did/ead:unitdate">
            <originInfo>
                <!-- Publisher -->
                <xsl:if test="/ead:ead/ead:archdesc/ead:bibliography[starts-with(ead:head,'Publication')]">
                    <xsl:for-each select="/ead:ead/ead:archdesc/ead:bibliography[starts-with(ead:head,'Publication')]">
                        <xsl:choose>
                            <!-- Split mulitple publishers -->
                            <xsl:when test="contains(ead:p,';')">
                                <xsl:for-each select="str:tokenize(ead:p,';')">
                                    <!-- parse place -->
                                    <place>
                                        <placeTerm type="text">
                                            <xsl:value-of select="normalize-space(substring-before(.,' : '))"/>
                                        </placeTerm>
                                    </place>
                                    <!-- parse publisher -->
                                    <publisher>
                                        <!-- parse date out of last publisher string -->
                                        <xsl:choose>
                                            <xsl:when test="'.' = substring(substring-after(.,' : '), string-length(substring-after(.,' : '))-string-length('.')+1)">
                                                <xsl:variable name="sl" select="string-length(substring-after(.,' : '))-5"/>
                                                <xsl:variable name="publisherStr" select="substring(substring-after(.,' : '),1,$sl)"/>
                                                <xsl:choose>
                                                    <xsl:when test="', ' = substring($publisherStr, string-length($publisherStr) - string-length(', ') +1)">
                                                        <xsl:value-of select="substring-before($publisherStr,', ')"/>
                                                    </xsl:when>
                                                    <xsl:otherwise>
                                                        <xsl:value-of select="$publisherStr"/>
                                                    </xsl:otherwise>
                                                </xsl:choose>
                                            </xsl:when>
                                            <xsl:otherwise>
                                                <xsl:value-of select="substring-after(.,' : ')"/>
                                            </xsl:otherwise>
                                        </xsl:choose>
                                    </publisher>
                                </xsl:for-each>
                            </xsl:when>
                            <xsl:when test="contains(ead:p,' : ')">
                                <!-- parse place -->
                                <place>
                                    <placeTerm type="text">
                                        <xsl:value-of select="normalize-space(substring-before(ead:p,' : '))"/>
                                    </placeTerm>
                                </place>
                                <!-- parse publisher -->
                                <publisher>
                                    <!-- parse date out of publisher string -->
                                    <xsl:choose>
                                        <xsl:when test="'.' = substring(substring-after(ead:p,' : '), string-length(substring-after(ead:p,' : ')) - string-length('.') +1)">
                                            <xsl:variable name="sl" select="string-length(substring-after(ead:p,' : '))-5"/>
                                            <xsl:variable name="publisherStr" select="substring(substring-after(ead:p,' : '),1,$sl)"/>
                                            <xsl:choose>
                                                <xsl:when test="', ' = substring($publisherStr, string-length($publisherStr) - string-length(', ') +1)">
                                                    <xsl:value-of select="substring-before($publisherStr,', ')"/>
                                                </xsl:when>
                                                <xsl:otherwise>
                                                    <xsl:value-of select="$publisherStr"/>
                                                </xsl:otherwise>
                                            </xsl:choose>
                                        </xsl:when>
                                        <xsl:otherwise>
                                            <xsl:value-of select="substring-after(ead:p,' : ')"/>
                                        </xsl:otherwise>
                                    </xsl:choose>
                                </publisher>
                            </xsl:when>
                            <xsl:otherwise>
                                <publisher>
                                    <xsl:value-of select="ead:p"/>
                                </publisher>
                            </xsl:otherwise>
                        </xsl:choose>
                    </xsl:for-each>
                </xsl:if>
                <!-- Date -->
                <xsl:for-each select="/ead:ead/ead:archdesc/ead:did/ead:unitdate">
                    <dateIssued>
                        <xsl:value-of select="."/>
                    </dateIssued>
                </xsl:for-each>
                <!-- Edition -->
                <xsl:for-each select="/ead:ead/ead:archdesc/ead:odd[starts-with(ead:head,'Edition Statement')]">
                    <edition>
                        <xsl:for-each select="ead:p">
                            <xsl:value-of select="."/><xsl:if test="position()!=last()"> </xsl:if>
                        </xsl:for-each>
                    </edition>
                </xsl:for-each>
            </originInfo>
        </xsl:if>
    </xsl:template>

    <!-- Collation -->
    <xsl:template name="physicalDesc">
           <xsl:if test="/ead:ead/ead:archdesc/ead:did/ead:physdesc/ead:extent">
            <physicalDescription>
                <xsl:for-each select="/ead:ead/ead:archdesc/ead:did/ead:physdesc/ead:extent">
                    <extent><xsl:value-of select="."/></extent>
                </xsl:for-each>
            </physicalDescription>
        </xsl:if>
    </xsl:template>

    <!-- Series -->
    <!-- NOTE: would be nice to be able to parse volume number into a part element, but don't see a "hook" -->
    <xsl:template name="series">
        <xsl:if test="/ead:ead/ead:archdesc/ead:odd[starts-with(ead:head,'Series')]">
            <xsl:variable name="titlestring">
                <xsl:for-each select="/ead:ead/ead:archdesc/ead:odd[starts-with(ead:head,'Series')]">
                    <xsl:value-of select="concat(ead:p,' ')"/>
                </xsl:for-each>
            </xsl:variable>
            <xsl:variable name="title">
                <xsl:choose>
                    <xsl:when test="' ' = substring($titlestring, string-length($titlestring) - string-length(' ') +1)">
                        <xsl:variable name="sl" select="string-length($titlestring)-1"/>
                        <xsl:value-of select="substring($titlestring,1,$sl)"/>
                    </xsl:when>
                    <xsl:otherwise>
                        <xsl:value-of select="$titlestring"/>
                    </xsl:otherwise>
                </xsl:choose>
            </xsl:variable>
            <relatedItem type="series">
                <titleInfo>
                    <title><xsl:value-of select="$title"/></title>
                </titleInfo>
            </relatedItem>
        </xsl:if>
    </xsl:template>

    <!-- Notes -->
    <xsl:template match="/ead:ead/ead:archdesc/ead:odd[starts-with(ead:head,'General')]">
        <note>
            <xsl:for-each select="ead:p">
                <xsl:value-of select="."/>
                <xsl:if test="position()!=last()"> </xsl:if>
            </xsl:for-each>
        </note>
    </xsl:template>

    <!-- Contents -->
    <xsl:template match="/ead:ead/ead:archdesc/ead:scopecontent">
        <abstract>
            <xsl:for-each select="ead:p">
                <xsl:value-of select="."/><xsl:if test="position()!=last()"> </xsl:if>
            </xsl:for-each>
        </abstract>
    </xsl:template>

    <!-- Controll Access Headings -->
    <xsl:template match="/ead:ead/ead:archdesc/ead:controlaccess">
        <xsl:for-each select="child::*[not(starts-with(@role,'aut'))]">
            <xsl:choose>
                <xsl:when test="self::ead:persname">
                    <subject>
                        <xsl:if test="@source != 'ingest'">
                            <xsl:attribute name="authority"><xsl:value-of select="@source"/></xsl:attribute>
                        </xsl:if>
                        <name type="personal">
                            <namePart><xsl:value-of select="normalize-space(.)"/></namePart>
                        </name>
                    </subject>
                </xsl:when>
                <xsl:when test="self::ead:corpname">
                    <subject>
                        <xsl:if test="@source != 'ingest'">
                            <xsl:attribute name="authority"><xsl:value-of select="@source"/></xsl:attribute>
                        </xsl:if>
                        <name type="corporate">
                            <namePart><xsl:value-of select="normalize-space(.)"/></namePart>
                        </name>
                    </subject>
                </xsl:when>
                <xsl:when test="self::ead:geogname">
                    <subject>
                        <xsl:if test="@source != 'ingest'">
                            <xsl:attribute name="authority"><xsl:value-of select="@source"/></xsl:attribute>
                        </xsl:if>
                        <geographic><xsl:value-of select="normalize-space(.)"/></geographic>
                    </subject>
                </xsl:when>
                <xsl:when test="self::ead:subject">
                    <subject>
                        <xsl:if test="@source != 'ingest'">
                            <xsl:attribute name="authority"><xsl:value-of select="@source"/></xsl:attribute>
                        </xsl:if>
                        <topic><xsl:value-of select="normalize-space(.)"/></topic>
                    </subject>
                </xsl:when>
                <xsl:otherwise>
                    <subject>
                        <xsl:if test="@source != 'ingest'">
                            <xsl:attribute name="authority"><xsl:value-of select="@source"/></xsl:attribute>
                        </xsl:if>
                        <topic><xsl:value-of select="normalize-space(.)"/></topic>
                    </subject>
                </xsl:otherwise>
            </xsl:choose>
        </xsl:for-each>
    </xsl:template>

    <!-- Provenance-->
    <xsl:template match="/ead:ead/ead:archdesc/ead:acqinfo[starts-with(ead:head,'Immediate Source of Acquisition')]">
        <note type="acquisition">
            <xsl:for-each select="ead:p">
                <xsl:value-of select="."/>
                <xsl:if test="position()!=last()"> </xsl:if>
            </xsl:for-each>
        </note>
    </xsl:template>

    <!-- Collection-->
    <xsl:template match="/ead:ead/ead:archdesc/ead:relatedmaterial">
        <relatedItem type="host">
            <titleInfo>
                <title>
                    <xsl:for-each select="ead:p">
                        <xsl:value-of select="."/>
                        <xsl:if test="position()!=last()"> </xsl:if>
                    </xsl:for-each>
                </title>
            </titleInfo>
        </relatedItem>
    </xsl:template>

    <!-- Duplicates-->
    <xsl:template match="/ead:ead/ead:archdesc/ead:originalsloc">
        <note type="original location">
            <xsl:for-each select="ead:p">
                <xsl:value-of select="."/>
                <xsl:if test="position()!=last()"> </xsl:if>
            </xsl:for-each>
        </note>
    </xsl:template>

    <!-- RAC Library-->
    <xsl:template match="/ead:ead/ead:archdesc/ead:altformavail">
        <note type="additional physical form">
            <xsl:for-each select="ead:p">
                <xsl:value-of select="."/>
                <xsl:if test="position()!=last()"> </xsl:if>
            </xsl:for-each>
        </note>
    </xsl:template>

    <!-- Identifiers-->
    <xsl:template match="/ead:ead/ead:archdesc/ead:fileplan[starts-with(ead:head,'ISBN')]">
        <identifier type="isbn"><xsl:value-of select="ead:p"/></identifier>
    </xsl:template>
    <xsl:template match="/ead:ead/ead:archdesc/ead:fileplan[starts-with(ead:head,'ISSN')]">
        <identifier type="issn"><xsl:value-of select="ead:p"/></identifier>
    </xsl:template>
    <xsl:template match="/ead:ead/ead:archdesc/ead:fileplan[starts-with(ead:head,'OCLC')]">
        <identifier type="oclc"><xsl:value-of select="ead:p"/></identifier>
    </xsl:template>
    <xsl:template match="/ead:ead/ead:archdesc/ead:fileplan[starts-with(ead:head,'LC')]">
        <identifier type="lccn"><xsl:value-of select="ead:p"/></identifier>
    </xsl:template>

    <!-- Item Type-->
    <xsl:template match="/ead:ead/ead:archdesc/ead:did/ead:container">
        <genre>
            <xsl:value-of select="@type"/>
        </genre>
        <!-- Call Nbr -->
        <classification><xsl:value-of select="."/></classification>
    </xsl:template>
</xsl:stylesheet>
